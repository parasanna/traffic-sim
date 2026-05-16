package com.multiagent.engine;

import com.multiagent.agents.*;
import com.multiagent.config.SimulationConfig;
import com.multiagent.events.EventManager;
import com.multiagent.metrics.MetricsCollector;
import com.multiagent.world.*;

import java.util.*;
import java.util.logging.Logger;

/**
 * Main simulation engine. Orchestrates the tick loop,
 * agent lifecycle, events, and metrics collection.
 */
public class SimulationEngine {
    private static final Logger logger = Logger.getLogger(SimulationEngine.class.getName());

    private final SimulationConfig config;
    private final GridWorld world;
    private final EventManager eventManager;
    private final MetricsCollector metrics;

    // Vehicles
    private final List<ResidentVehicle> residents = new ArrayList<>();
    private final List<TransientVehicle> transients = new ArrayList<>();
    private final List<FoodTruck> foodTrucks = new ArrayList<>();
    private final List<GarbageTruck> garbageTrucks = new ArrayList<>();
    private final List<BaseVehicle> allVehicles = new ArrayList<>();

    // State
    private long currentTick = 0;
    private int currentDay = 0;
    private int currentZone = 0;
    private boolean running = false;

    // Transient spawning
    private double transientAccumulator = 0;
    private long lastServiceSpawn = 0;

    // Active counts
    private int activeResidents = 0;
    private int activeTransients = 0;
    private int activeFoodTrucks = 0;
    private int activeGarbageTrucks = 0;

    public SimulationEngine(SimulationConfig config, long seed) {
        this.config = config;

        // Create world
        this.world = new GridWorld(config, seed);
        world.generate();

        // Create managers
        this.eventManager = new EventManager(world, config);
        this.metrics = new MetricsCollector();

        // Initialize agents
        initializeResidents();

        logger.info("Simulation engine initialized: " + config);
    }

    /**
     * Initialize resident vehicles (P1).
     * We use a scaled-down version: actual residents based on available blocks.
     */
    private void initializeResidents() {
        List<BuildingBlock> residentialBlocks = world.getBlocksByCategory(BlockCategory.RESIDENTIAL);
        if (residentialBlocks.isEmpty()) {
            logger.warning("No residential blocks found! Using all blocks.");
            residentialBlocks = new ArrayList<>(world.getBlocks());
        }

        // Scale: place a number of residents proportional to available blocks
        int maxResidents = Math.min(config.residentPopulation,
            residentialBlocks.size() * 50); // Up to 50 per block
        // For performance, limit to a manageable number
        int numResidents = Math.min(maxResidents, 500);

        for (int i = 0; i < numResidents; i++) {
            BuildingBlock home = residentialBlocks.get(i % residentialBlocks.size());
            if (home.getEntryExitPoints().isEmpty()) continue;

            ResidentVehicle resident = new ResidentVehicle(world, config);
            resident.setHomeBlock(home);
            residents.add(resident);
            allVehicles.add(resident);
        }

        logger.info(String.format("Initialized %d residents", residents.size()));
    }

    /**
     * Run the simulation for the configured number of ticks.
     */
    public void run() {
        running = true;
        logger.info("=== Simulation Starting ===");
        logger.info(String.format("Total ticks: %d (%.1f days)",
            config.observationTicks, (double) config.observationTicks / config.ticksPerDay()));

        long startTime = System.currentTimeMillis();

        while (currentTick < config.observationTicks && running) {
            tick();

            // Log progress every 1000 ticks
            if (currentTick % 1000 == 0) {
                logProgress();
            }
        }

        long elapsed = System.currentTimeMillis() - startTime;
        logger.info(String.format("=== Simulation Complete === (%.1f seconds)", elapsed / 1000.0));
        printFinalReport();
    }

    /**
     * Execute a single simulation tick.
     */
    public void tick() {
        // Update day and time zone
        int newDay = (int) (currentTick / config.ticksPerDay());
        int newZone = config.getTimeZone(currentTick);

        if (newDay > currentDay) {
            currentDay = newDay;
            metrics.onNewDay(currentDay);
            logger.info(String.format("=== Day %d ===", currentDay + 1));
        }

        if (newZone != currentZone) {
            currentZone = newZone;
            logger.fine(String.format("Zone change: %s", config.getZoneLabel(currentZone)));
        }

        // 1. Update traffic lights
        world.updateTrafficLights(currentTick);

        // 2. Update resources (food consumption, pollution production)
        world.updateResources(currentTick);

        // 3. Spawn transient vehicles (#14)
        spawnTransients();

        // 4. Spawn service vehicles (#12)
        spawnServiceVehicles();

        // 5. Make decisions for all agents
        double intensity = config.getTrafficIntensity(currentZone);
        for (ResidentVehicle r : residents) {
            if (world.getRandom().nextDouble() < intensity) {
                r.decide(currentTick, currentZone);
            }
        }
        for (FoodTruck ft : foodTrucks) ft.decide(currentTick, currentZone);
        for (GarbageTruck gt : garbageTrucks) gt.decide(currentTick, currentZone);

        // 6. Update all vehicles (movement)
        for (BaseVehicle v : allVehicles) {
            v.update(currentTick);
        }

        // 7. Update events (storms, accidents)
        eventManager.update(currentTick, allVehicles);

        // 8. Cleanup completed vehicles
        cleanupVehicles();

        // 9. Update active counts
        updateCounts();

        currentTick++;
    }

    /**
     * Spawn transient vehicles based on P2 rate.
     */
    private void spawnTransients() {
        transientAccumulator += config.transientSpawnRate();
        while (transientAccumulator >= 1.0) {
            TransientVehicle tv = new TransientVehicle(world, config);
            if (tv.spawn(currentTick)) {
                transients.add(tv);
                allVehicles.add(tv);
                metrics.recordTransitEntry();
            }
            transientAccumulator -= 1.0;
        }
    }

    /**
     * Spawn service vehicles (food/garbage) at intervals (#12).
     */
    private void spawnServiceVehicles() {
        if (currentTick - lastServiceSpawn >= config.serviceInterval) {
            lastServiceSpawn = currentTick;

            // Spawn food trucks if needed
            int activeFT = (int) foodTrucks.stream()
                .filter(ft -> ft.getState() != VehicleState.COMPLETED).count();
            if (activeFT < config.supplyFleetSize) {
                FoodTruck ft = new FoodTruck(world, config);
                if (ft.spawn(currentTick)) {
                    foodTrucks.add(ft);
                    allVehicles.add(ft);
                }
            }

            // Spawn garbage trucks if needed
            int activeGT = (int) garbageTrucks.stream()
                .filter(gt -> gt.getState() != VehicleState.COMPLETED).count();
            if (activeGT < config.collectionFleetSize) {
                GarbageTruck gt = new GarbageTruck(world, config);
                if (gt.spawn(currentTick)) {
                    garbageTrucks.add(gt);
                    allVehicles.add(gt);
                }
            }
        }
    }

    /**
     * Remove completed vehicles from active lists.
     */
    private void cleanupVehicles() {
        transients.removeIf(v -> v.getState() == VehicleState.COMPLETED);
        foodTrucks.removeIf(v -> v.getState() == VehicleState.COMPLETED);
        garbageTrucks.removeIf(v -> v.getState() == VehicleState.COMPLETED);
    }

    private void updateCounts() {
        activeResidents = (int) residents.stream().filter(BaseVehicle::isActive).count();
        activeTransients = transients.size();
        activeFoodTrucks = (int) foodTrucks.stream()
            .filter(v -> v.getState() != VehicleState.COMPLETED).count();
        activeGarbageTrucks = (int) garbageTrucks.stream()
            .filter(v -> v.getState() != VehicleState.COMPLETED).count();
    }

    private void logProgress() {
        int totalActive = activeResidents + activeTransients + activeFoodTrucks + activeGarbageTrucks;
        logger.info(String.format("Tick %d | Day %d | Zone %d (%s) | Active: %d (R:%d T:%d F:%d G:%d) | Storms: %d",
            currentTick, currentDay + 1, currentZone, config.getZoneLabel(currentZone),
            totalActive, activeResidents, activeTransients, activeFoodTrucks, activeGarbageTrucks,
            eventManager.getActiveStorms().size()));
    }

    private void printFinalReport() {
        System.out.println("\n╔══════════════════════════════════════════╗");
        System.out.println("║     ΤΕΛΙΚΗ ΑΝΑΦΟΡΑ ΠΡΟΣΟΜΟΙΩΣΗΣ          ║");
        System.out.println("╠══════════════════════════════════════════╣");
        System.out.printf("║ Ticks: %-34d ║%n", currentTick);
        System.out.printf("║ Days: %-35d ║%n", currentDay + 1);
        System.out.printf("║ Roads: %-34d ║%n", world.getRoads().size());
        System.out.printf("║ Blocks: %-33d ║%n", world.getBlocks().size());
        System.out.printf("║ Entries: %-32d ║%n", world.getBorderEntries().size());
        System.out.printf("║ Exits: %-34d ║%n", world.getBorderExits().size());
        System.out.println("╠══════════════════════════════════════════╣");
        System.out.printf("║ Residents: %-30d ║%n", residents.size());
        System.out.printf("║ Storms Total: %-27d ║%n", eventManager.getTotalStormsCreated());
        System.out.printf("║ Accidents: %-30d ║%n", eventManager.getTotalAccidents());
        System.out.println("╠══════════════════════════════════════════╣");

        Map<String, Object> m = metrics.getSummary();
        System.out.printf("║ Avg Transit Time: %-23s ║%n", m.get("avgTransitTime"));
        System.out.printf("║ Avg Internal Time: %-22s ║%n", m.get("avgInternalTime"));
        System.out.printf("║ Transit Time/Length: %-20s ║%n", m.get("avgTransitTimePerLength"));
        System.out.printf("║ Internal Time/Length: %-19s ║%n", m.get("avgInternalTimePerLength"));
        System.out.printf("║ Flow Difference: %-24s ║%n", m.get("flowDifference"));
        System.out.println("╚══════════════════════════════════════════╝");
    }

    // ========== Public API for Dashboard ==========

    public void stop() { running = false; }
    public long getCurrentTick() { return currentTick; }
    public int getCurrentDay() { return currentDay; }
    public int getCurrentZone() { return currentZone; }
    public GridWorld getWorld() { return world; }
    public SimulationConfig getConfig() { return config; }
    public EventManager getEventManager() { return eventManager; }
    public MetricsCollector getMetrics() { return metrics; }
    public List<BaseVehicle> getAllVehicles() { return allVehicles; }
    public int getActiveResidents() { return activeResidents; }
    public int getActiveTransients() { return activeTransients; }
    public int getActiveFoodTrucks() { return activeFoodTrucks; }
    public int getActiveGarbageTrucks() { return activeGarbageTrucks; }
    public boolean isRunning() { return running; }
}
