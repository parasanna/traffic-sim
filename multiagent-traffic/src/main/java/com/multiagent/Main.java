package com.multiagent;

import com.multiagent.config.SimulationConfig;
import com.multiagent.engine.SimulationEngine;
import com.multiagent.server.DashboardServer;

import java.util.logging.*;

/**
 * Main entry point for the Multi-Agent Traffic Simulation.
 * 
 * Usage:
 *   java -jar multiagent-traffic.jar [options]
 * 
 * Options:
 *   --ticks N       Total simulation ticks (default: 201600 = 1 week)
 *   --rows N        Grid rows (default: 200)
 *   --cols N        Grid columns (default: 200)
 *   --port N        Dashboard port (default: 8080)
 *   --no-server     Run without web dashboard
 *   --seed N        Random seed (default: 42)
 *   --fast          Reduced grid for fast testing (50x60)
 *   --log LEVEL     Log level: INFO, FINE, etc.
 */
public class Main {
    private static final Logger logger = Logger.getLogger(Main.class.getName());

    public static void main(String[] args) {
        // Parse arguments
        SimulationConfig config = new SimulationConfig();
        int port = 8080;
        boolean noServer = false;
        long seed = 42;
        String logLevel = "INFO";

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--ticks" -> config.observationTicks = Integer.parseInt(args[++i]);
                case "--rows" -> config.gridRows = Integer.parseInt(args[++i]);
                case "--cols" -> config.gridCols = Integer.parseInt(args[++i]);
                case "--port" -> port = Integer.parseInt(args[++i]);
                case "--no-server" -> noServer = true;
                case "--seed" -> seed = Long.parseLong(args[++i]);
                case "--population" -> config.residentPopulation = Integer.parseInt(args[++i]);
                case "--transient" -> config.transientDaily = Integer.parseInt(args[++i]);
                case "--fast" -> {
                    config.gridRows = 50;
                    config.gridCols = 60;
                    config.observationTicks = 5000;
                    config.residentPopulation = 100;
                    config.transientDaily = 50;
                }
                case "--log" -> logLevel = args[++i];
                case "--help" -> {
                    printHelp();
                    return;
                }
            }
        }

        // Configure logging
        setupLogging(logLevel);

        System.out.println("╔══════════════════════════════════════════╗");
        System.out.println("║  🏙️  Multi-Agent Traffic Simulation      ║");
        System.out.println("║      Πολυπρακτορικό Σύστημα Κυκλοφορίας  ║");
        System.out.println("╚══════════════════════════════════════════╝");
        System.out.println();
        System.out.println("Configuration: " + config);
        System.out.println();

        // Create simulation engine
        SimulationEngine engine = new SimulationEngine(config, seed);

        // Start dashboard server
        DashboardServer dashboard = null;
        if (!noServer) {
            try {
                dashboard = new DashboardServer(port);
                dashboard.start(engine);
                System.out.println("🌐 Dashboard: http://localhost:" + port);
                System.out.println();
            } catch (Exception e) {
                logger.warning("Could not start dashboard server: " + e.getMessage());
            }
        }

        // Run simulation
        try {
            engine.run();
        } catch (Exception e) {
            logger.severe("Simulation error: " + e.getMessage());
            e.printStackTrace();
        } finally {
            if (dashboard != null) {
                // Keep server running for a bit so user can see final state
                try { Thread.sleep(5000); } catch (InterruptedException ignored) {}
                dashboard.stop();
            }
        }
    }

    private static void setupLogging(String level) {
        Logger rootLogger = Logger.getLogger("");
        rootLogger.setLevel(Level.parse(level));
        for (Handler handler : rootLogger.getHandlers()) {
            handler.setLevel(Level.parse(level));
            handler.setFormatter(new SimpleFormatter() {
                @Override
                public String format(LogRecord record) {
                    return String.format("[%s] %s: %s%n",
                        record.getLevel(), record.getLoggerName().replace("com.multiagent.", ""),
                        record.getMessage());
                }
            });
        }
    }

    private static void printHelp() {
        System.out.println("Multi-Agent Traffic Simulation");
        System.out.println();
        System.out.println("Options:");
        System.out.println("  --ticks N       Total simulation ticks (default: 201600)");
        System.out.println("  --rows N        Grid rows (default: 200)");
        System.out.println("  --cols N        Grid columns (default: 200)");
        System.out.println("  --port N        Dashboard port (default: 8080)");
        System.out.println("  --no-server     Run without web dashboard");
        System.out.println("  --seed N        Random seed (default: 42)");
        System.out.println("  --population N  Resident population (default: 100000)");
        System.out.println("  --transient N   Daily transient count (default: 24000)");
        System.out.println("  --fast          Fast mode (small grid, few ticks)");
        System.out.println("  --log LEVEL     Log level (default: INFO)");
        System.out.println("  --help          Show this help");
    }
}
