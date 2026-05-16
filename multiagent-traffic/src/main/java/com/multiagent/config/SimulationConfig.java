package com.multiagent.config;

/**
 * Configuration parameters for the Multi-Agent Urban Traffic Simulation.
 * All values match the specifications from the problem document.
 * Parameters are numbered 1-31 as defined in the specification table.
 */
public class SimulationConfig {

    // --- #1: Time unit ---
    /** 1 tick = 3 seconds of real time */
    public static final double TICK_SECONDS = 3.0;

    // --- #2: Observation period ---
    /** Total simulation ticks = 1 week = 7 * 24 * 60 * 20 = 201600 ticks */
    public int observationTicks = 7 * 24 * 60 * 20; // 201600

    // --- #3: World size ---
    /** Grid rows (GR) */
    public int gridRows = 200;
    /** Grid columns (GC) */
    public int gridCols = 200;

    // --- #4: Number of blocks (buildings) ---
    /** Minimum number of blocks (Τετράγωνα, Κτίρια) */
    public int minBlocks = 20;

    // --- #5: Block size ---
    /** Block size as percentage of total world area: 100-2% * AW cells */
    public double blockSizeMinPercent = 0.002; // 0.2% of AW (smallest)
    public double blockSizeMaxPercent = 0.01;  // 1% of AW

    // --- #6: Number of roads ---
    /** Minimum number of roads */
    public int minRoads = 10;

    // --- #7: Agent perception radius ---
    /** Perception radius R (in cells, per direction) */
    public int perceptionRadius = 10;

    // --- #8: Supply fleet size (M) ---
    /** Number of supply (food) vehicles */
    public int supplyFleetSize = 200;

    // --- #9: Supply vehicle capacity (M1) ---
    /** Capacity per supply vehicle in "FOOD" units */
    public int supplyCapacity = 50;

    // --- #10: Collection fleet size (N) ---
    /** Number of waste collection vehicles */
    public int collectionFleetSize = 50;

    // --- #11: Collection vehicle capacity (N1) ---
    /** Capacity per waste collection vehicle in "POLLUTION" units */
    public int collectionCapacity = 250;

    // --- #12: Service vehicle entry interval (SI) ---
    /** Ticks between new service vehicle entries = 20 * 180 = 3600 ticks (3 hours) */
    public int serviceInterval = 20 * 180; // 3600 ticks

    // --- #13: Resident population (P1) ---
    /** Total permanent residents with vehicles */
    public int residentPopulation = 100_000;

    // --- #14: Transient population (P2) ---
    /** Daily transient vehicles passing through (per 24h) */
    public int transientDaily = 24_000;

    // --- #15: Max simultaneous storms (S) ---
    public int maxStorms = 3;

    // --- #16: Storm reappearance time (SRE) ---
    /** Ticks before a new storm can appear = 4 * 24 * 60 * 20 = 115200 ticks (4 days) */
    public int stormReappearanceTime = 4 * 24 * 60 * 20;

    // --- #17: Storm radius (SR) ---
    /** Storm radius range in cells */
    public int stormRadiusMin = 50;
    public int stormRadiusMax = 100;

    // --- #18: Speed reduction due to storm (VR) ---
    /** Speed reduction per tick while in storm area. V >= 0 always */
    public int stormSpeedReduction = 2;

    // --- #19: Mechanical failure probability (PMF) ---
    /** Probability of breakdown per tick per vehicle */
    public double breakdownProbability = 1e-7;

    // --- #20: Breakdown immobilization time (MD) ---
    /** Ticks a vehicle is immobilized after breakdown = 400 ticks (20 mins) */
    public int breakdownDuration = 400;

    // --- #21: Service duration (SD) ---
    /** Service time at a block = A / 4 ticks, where A is the block area */
    public double serviceTimeFactor = 0.25; // A / 4

    // --- #22: Accident probability (PA) ---
    /** Probability of accident per qualifying vehicle pair per tick */
    public double accidentProbability = 1e-3;

    // --- #23: Accident immobilization time (AD) ---
    /** Ticks a vehicle is immobilized after accident = 600 ticks (30 mins) */
    public int accidentDuration = 600;

    // --- #24: Food consumption rate (FCR) ---
    /** Food units consumed per cell per 50 ticks */
    public double foodConsumptionRate = 1.0 / 50.0; // 1 unit per 50 ticks per cell

    // --- #25: Food storage factor (F) ---
    /** Max food storage per cell = F units/cell */
    public double foodStorageFactor = 2.0;

    // --- #26: Max food storage ---
    /** Max food = F * A (A = block area), computed dynamically */

    // --- #27: Pollution generation rate (PGR) ---
    /** Pollution units produced per cell per 100 ticks */
    public double pollutionRate = 1.0 / 100.0; // 1 unit per 100 ticks per cell

    // --- #28: Pollution storage factor (P) ---
    /** Max pollution per cell */
    public double pollutionStorageFactor = 1.5;

    // --- #29: Max pollution storage ---
    /** Max pollution = P * A, computed dynamically */

    // --- #30: Minimum road area (RAT) ---
    /** Minimum road area in cells */
    public int minRoadArea = 10;

    // --- #31: Vehicle speed (V) ---
    /** 0 = stopped, otherwise random [1, 5] cells/tick per movement episode */
    public int minSpeed = 1;
    public int maxSpeed = 5;

    // ============ Derived / Convenience Constants ============

    /** Ticks per day = 24 * 60 * 20 = 28800 */
    public int ticksPerDay() { return 24 * 60 * 20; }

    /** Ticks per hour = 60 * 20 = 1200 */
    public int ticksPerHour() { return 60 * 20; }

    /** Total world area in cells */
    public int worldArea() { return gridRows * gridCols; }

    /** Transient vehicles per tick = P2 / ticksPerDay */
    public double transientSpawnRate() { return (double) transientDaily / ticksPerDay(); }

    // ============ Time Zones (8 zones per day) ============

    /**
     * Returns the time zone index (0-7) for the given tick within a day.
     * Zone 0: 00:00-03:00 (Night/Low traffic)
     * Zone 1: 03:00-06:00 (Early morning)
     * Zone 2: 06:00-09:00 (Morning rush)
     * Zone 3: 09:00-12:00 (Late morning)
     * Zone 4: 12:00-15:00 (Afternoon)
     * Zone 5: 15:00-18:00 (Evening rush)
     * Zone 6: 18:00-21:00 (Evening)
     * Zone 7: 21:00-00:00 (Late night)
     */
    public int getTimeZone(long tick) {
        int tickInDay = (int) (tick % ticksPerDay());
        int hour = tickInDay / ticksPerHour();
        return hour / 3; // 8 zones of 3 hours each
    }

    /**
     * Returns a human-readable zone label.
     */
    public String getZoneLabel(int zone) {
        return switch (zone) {
            case 0 -> "Night (00-03)";
            case 1 -> "Early Morning (03-06)";
            case 2 -> "Morning Rush (06-09)";
            case 3 -> "Late Morning (09-12)";
            case 4 -> "Afternoon (12-15)";
            case 5 -> "Evening Rush (15-18)";
            case 6 -> "Evening (18-21)";
            case 7 -> "Late Night (21-00)";
            default -> "Unknown";
        };
    }

    /**
     * Traffic intensity multiplier per zone (0.0 to 1.0).
     * Determines what fraction of vehicles are active.
     */
    public double getTrafficIntensity(int zone) {
        return switch (zone) {
            case 0 -> 0.05;  // Night
            case 1 -> 0.15;  // Early morning
            case 2 -> 0.85;  // Morning rush
            case 3 -> 0.60;  // Late morning
            case 4 -> 0.50;  // Afternoon
            case 5 -> 0.90;  // Evening rush
            case 6 -> 0.55;  // Evening
            case 7 -> 0.20;  // Late night
            default -> 0.30;
        };
    }

    @Override
    public String toString() {
        return String.format(
            "SimulationConfig{grid=%dx%d, blocks≥%d, roads≥%d, P1=%d, P2=%d/day, " +
            "M=%d(cap=%d), N=%d(cap=%d), storms≤%d, ticks=%d}",
            gridRows, gridCols, minBlocks, minRoads, residentPopulation, transientDaily,
            supplyFleetSize, supplyCapacity, collectionFleetSize, collectionCapacity,
            maxStorms, observationTicks
        );
    }
}
