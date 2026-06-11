// bz-pool-miner — native BLOZ pool miner (RandomX + Stratum/WSS)
// Started by blockzero-ops: mine-mainnet.ps1 -Pool (Windows) / mine-pool.sh (Linux, macOS)

#include "miner_config.hpp"
#include "pow_util.hpp"
#include "stratum_client.hpp"

#include <ixwebsocket/IXNetSystem.h>
#include <randomx.h>

#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <memory>
#include <mutex>
#include <thread>
#include <vector>

namespace {

constexpr int kMaxThreads = 64;

struct RxCache {
    randomx_cache* ptr{nullptr};
    explicit RxCache(randomx_cache* cache) : ptr(cache) {}
    ~RxCache() {
        if (ptr) randomx_release_cache(ptr);
    }
};

randomx_flags MiningFlags() {
    randomx_flags flags = randomx_get_flags();
#ifdef _WIN32
    // JIT can crash on some Windows setups; compiled mode is slower but stable.
    flags = static_cast<randomx_flags>(flags & ~RANDOMX_FLAG_JIT);
#endif
    return flags;
}

struct ActiveJob {
    std::string id;
    std::vector<uint8_t> header_prefix;
    uint8_t pool_target_be[32]{};
    randomx_flags flags{};
    std::shared_ptr<RxCache> cache;
    std::string rx_key_hex;
};

std::mutex g_job_mu;
ActiveJob g_job;
std::atomic<bool> g_stop{false};
std::atomic<uint64_t> g_hashes{0};
pool::StratumClient* g_client{nullptr};

bool ApplyJob(const pool::MiningJob& mj) {
    auto prefix = pool::HexDecode(mj.header_prefix_hex);
    auto key = pool::HexDecode(mj.rx_key_hex);
    if (prefix.size() < 76 || key.size() != 32) {
        std::cerr << "Ignored invalid job " << mj.job_id << "\n";
        return false;
    }

    // Reuse the existing RandomX cache when the key is unchanged. Cache init
    // takes seconds; jobs change every block but the key only every epoch.
    std::shared_ptr<RxCache> cache_holder;
    {
        std::lock_guard<std::mutex> lock(g_job_mu);
        if (g_job.cache && g_job.rx_key_hex == mj.rx_key_hex) {
            cache_holder = g_job.cache;
        }
    }

    const randomx_flags flags = MiningFlags();
    if (!cache_holder) {
        randomx_cache* raw_cache = randomx_alloc_cache(flags);
        if (!raw_cache) {
            std::cerr << "RandomX cache allocation failed (low memory?)\n";
            return false;
        }
        randomx_init_cache(raw_cache, key.data(), key.size());
        cache_holder = std::make_shared<RxCache>(raw_cache);
    }

    {
        std::lock_guard<std::mutex> lock(g_job_mu);
        g_job.id = mj.job_id;
        g_job.header_prefix = std::move(prefix);
        g_job.flags = flags;
        g_job.cache = cache_holder;
        g_job.rx_key_hex = mj.rx_key_hex;
        pool::HexToTargetBe(mj.pool_target_hex, g_job.pool_target_be);
    }

    std::cout << "New job: " << mj.job_id << " - mining.\n";
    std::cout.flush();
    return true;
}

void GrindThread(int thread_id, int thread_count) {
    std::vector<uint8_t> header(80);
    uint8_t hash[32];

    while (!g_stop.load()) {
        std::string job_id;
        std::vector<uint8_t> header_prefix;
        uint8_t pool_target_be[32]{};
        randomx_flags flags{};
        std::shared_ptr<RxCache> cache_holder;

        {
            std::lock_guard<std::mutex> lock(g_job_mu);
            if (!g_job.cache || g_job.header_prefix.size() < 76) {
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
                continue;
            }
            job_id = g_job.id;
            header_prefix = g_job.header_prefix;
            std::memcpy(pool_target_be, g_job.pool_target_be, 32);
            flags = g_job.flags;
            cache_holder = g_job.cache;
        }

        randomx_vm* vm = randomx_create_vm(flags, cache_holder->ptr, nullptr);
        if (!vm) {
            std::cerr << "RandomX VM init failed on thread " << thread_id << "\n";
            std::this_thread::sleep_for(std::chrono::milliseconds(250));
            continue;
        }

        std::memcpy(header.data(), header_prefix.data(), 76);
        uint64_t nonce = static_cast<uint32_t>(thread_id);
        const uint64_t step = static_cast<uint64_t>(thread_count);

        while (!g_stop.load()) {
            {
                std::lock_guard<std::mutex> lock(g_job_mu);
                if (g_job.id != job_id) break;
            }

            for (int burst = 0; burst < 500; ++burst) {
                const uint32_t n = static_cast<uint32_t>(nonce);
                std::memcpy(header.data() + 76, &n, 4);
                randomx_calculate_hash(vm, header.data(), header.size(), hash);

                if (pool::HashMeetsTarget(hash, pool_target_be)) {
                    std::cout << "Share found (nonce=" << n << ") - submitting...\n";
                    std::cout.flush();
                    if (g_client) g_client->SubmitShare(job_id, n);
                }
                nonce += step;
            }
            g_hashes.fetch_add(500, std::memory_order_relaxed);
        }

        randomx_destroy_vm(vm);
    }
}

void ReportThread() {
    auto t0 = std::chrono::steady_clock::now();
    uint64_t last = 0;
    while (!g_stop.load()) {
        for (int i = 0; i < 300 && !g_stop.load(); ++i) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        if (g_stop.load()) break;
        const uint64_t now_hashes = g_hashes.load(std::memory_order_relaxed);
        const auto now = std::chrono::steady_clock::now();
        const double sec = std::chrono::duration<double>(now - t0).count();
        if (sec <= 0) continue;
        const double rate = static_cast<double>(now_hashes - last) / sec;
        last = now_hashes;
        t0 = now;
        const uint64_t acc = g_client ? g_client->AcceptedShares() : 0;
        const uint64_t rej = g_client ? g_client->RejectedShares() : 0;
        std::printf("Hashrate: %.0f H/s | shares: %llu accepted",
                    rate, static_cast<unsigned long long>(acc));
        if (rej > 0) std::printf(", %llu rejected", static_cast<unsigned long long>(rej));
        std::printf("\n");
        std::fflush(stdout);
    }
}

bool MatchesThreadsArg(const std::string& arg) {
    return arg == "-t" || arg == "--threads" || arg == "-Threads" || arg == "--Threads";
}

void PrintBlockZeroHint() {
    std::cerr << "\nThis miner is started by BlockZero (blockzero-ops).\n";
    std::cerr << "Windows:\n";
    std::cerr << "  cd blockzero-ops\\scripts\\mainnet\n";
    std::cerr << "  .\\mine-mainnet.ps1 -Pool\n";
    std::cerr << "Linux/macOS:\n";
    std::cerr << "  cd blockzero-ops/scripts/mainnet\n";
    std::cerr << "  ./mine-pool.sh\n\n";
}

void PrintUsage(const char* argv0) {
    std::fprintf(stderr,
        "Usage: %s -o pool_url -u bz1ADDR.rig [-Threads N]\n"
        "\n"
        "End users: run BlockZero pool mining instead:\n"
        "  Windows:     mine-mainnet.ps1 -Pool\n"
        "  Linux/macOS: mine-pool.sh\n"
        "\n"
        "  -Threads N   CPU threads (1-%d). Also: -t, --threads\n",
        argv0, kMaxThreads);
}

} // namespace

int main(int argc, char* argv[]) {
    SetupConsole();

    if (!ix::initNetSystem()) {
        std::cerr << "Network init failed (WSAStartup).\n";
        PauseBeforeExit(1);
        return 1;
    }

    std::string url;
    std::string worker;
    std::string password = "x";
    int threads = 0;
    bool help = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if ((arg == "-o" || arg == "--url") && i + 1 < argc) url = argv[++i];
        else if ((arg == "-u" || arg == "--user") && i + 1 < argc) worker = argv[++i];
        else if ((arg == "-p" || arg == "--pass") && i + 1 < argc) password = argv[++i];
        else if (MatchesThreadsArg(arg) && i + 1 < argc) threads = std::atoi(argv[++i]);
        else if (arg == "-h" || arg == "--help") help = true;
    }

    if (help) {
        PrintUsage(argv[0]);
        ix::uninitNetSystem();
        return 0;
    }

    MinerConfig cfg;
    const std::string conf_path = DefaultConfigPath();

    if (worker.empty()) {
        if (!LoadConfig(conf_path, cfg)) {
            PrintBlockZeroHint();
            ix::uninitNetSystem();
            PauseBeforeExit(1);
            return 1;
        }
        worker = BuildWorker(cfg);
        if (url.empty()) url = cfg.pool_url;
        if (threads <= 0) threads = ResolveThreads(cfg);
    } else {
        if (url.empty()) url = "wss://pool.bloz.org/stratum";
        if (threads <= 0) threads = ResolveThreads(cfg);
    }

    // Clamp instead of erroring out - users should never see a hard failure
    // for asking for too many threads.
    if (threads < 1) threads = 1;
    if (threads > kMaxThreads) {
        std::cout << "Requested " << threads << " threads - capping at " << kMaxThreads << ".\n";
        threads = kMaxThreads;
    }
    const int cores = static_cast<int>(std::thread::hardware_concurrency());
    if (cores > 0 && threads > cores) {
        std::cout << "Note: " << threads << " threads on " << cores
                  << " logical cores - using " << cores << ".\n";
        threads = cores;
    }

    if (worker.find("bz1") != 0 || worker.find('.') == std::string::npos) {
        std::fprintf(stderr, "Worker must be bz1ADDRESS.rigname (got: %s)\n", worker.c_str());
        std::fprintf(stderr, "Delete miner.conf and run again, or fix BZ1_ADDRESS.\n");
        ix::uninitNetSystem();
        PauseBeforeExit(1);
        return 1;
    }

    std::cout << "Connecting to pool...\n";
    std::cout << "Pool:    " << url << "\n";
    std::cout << "Worker:  " << worker << "\n";
    std::cout << "Threads: " << threads << "\n";
    std::cout << "Config:  " << conf_path << "\n";
    std::cout << "Press Ctrl+C to stop.\n\n";
    std::cout.flush();

    pool::StratumClient client(url, worker, password);
    g_client = &client;
    client.SetJobCallback([](const pool::MiningJob& job) { ApplyJob(job); });

    std::signal(SIGINT, [](int) { g_stop.store(true); });
    std::signal(SIGTERM, [](int) { g_stop.store(true); });

    client.Start(); // keeps retrying in the background even if first connect fails

    std::vector<std::thread> workers;
    workers.reserve(threads + 1);
    for (int t = 0; t < threads; ++t) {
        workers.emplace_back(GrindThread, t, threads);
    }
    workers.emplace_back(ReportThread);

    while (!g_stop.load()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
    }

    for (auto& w : workers) {
        if (w.joinable()) w.join();
    }

    client.Stop();
    {
        std::lock_guard<std::mutex> lock(g_job_mu);
        g_job.cache.reset();
    }

    std::cout << "\nMiner stopped.\n";
    std::cout.flush();
    ix::uninitNetSystem();
    return 0;
}
