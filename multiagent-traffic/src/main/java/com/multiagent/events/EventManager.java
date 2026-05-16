package com.multiagent.events;

import com.multiagent.agents.BaseVehicle;
import com.multiagent.config.SimulationConfig;
import com.multiagent.world.*;
import java.util.*;
import java.util.logging.Logger;

/**
 * Manages all simulation events: storms, breakdowns, accidents.
 */
public class EventManager {
    private static final Logger logger = Logger.getLogger(EventManager.class.getName());

    private final GridWorld world;
    private final SimulationConfig config;
    private final Random random;

    // Storms
    private final List<Storm> activeStorms = new ArrayList<>();
    private long lastStormTick = -999999;
    private int totalStormsCreated = 0;

    // Statistics
    private int totalBreakdowns = 0;
    private int totalAccidents = 0;

    public EventManager(GridWorld world, SimulationConfig config) {
        this.world = world;
        this.config = config;
        this.random = world.getRandom();
    }

    /**
     * Update all events for the current tick.
     */
    public void update(long currentTick, List<? extends BaseVehicle> vehicles) {
        updateStorms(currentTick);
        applyStormEffects();
        checkAccidents(currentTick, vehicles);
    }

    // ========== Storm Management ==========

    private void updateStorms(long currentTick) {
        // Remove expired storms
        activeStorms.removeIf(s -> {
            s.update(currentTick);
            return !s.isActive();
        });

        // Try to spawn new storms (#15: max S simultaneous, #16: SRE reappearance)
        if (activeStorms.size() < config.maxStorms &&
            currentTick - lastStormTick >= config.stormReappearanceTime) {

            // Random chance to spawn a storm
            if (random.nextDouble() < 0.001) { // Low probability each tick
                spawnStorm(currentTick);
            }
        }
    }

    private void spawnStorm(long currentTick) {
        int centerRow = random.nextInt(world.getRows());
        int centerCol = random.nextInt(world.getCols());
        int radius = config.stormRadiusMin +
            random.nextInt(config.stormRadiusMax - config.stormRadiusMin + 1);

        // Storm duration: 1-6 hours (random)
        long duration = (1 + random.nextInt(6)) * config.ticksPerHour();

        Storm storm = new Storm(centerRow, centerCol, radius,
            currentTick, duration, config.stormSpeedReduction);
        activeStorms.add(storm);
        lastStormTick = currentTick;
        totalStormsCreated++;

        logger.info(String.format("Storm spawned at (%d,%d) r=%d, duration=%d ticks",
            centerRow, centerCol, radius, duration));
    }

    private void applyStormEffects() {
        // Reset all storm effects
        for (int r = 0; r < world.getRows(); r++) {
            for (int c = 0; c < world.getCols(); c++) {
                world.getCell(r, c).setStormSpeedReduction(0);
            }
        }

        // Apply active storm effects
        for (Storm storm : activeStorms) {
            // Only iterate within storm radius to save computation
            int minR = Math.max(0, storm.centerRow - storm.radius);
            int maxR = Math.min(world.getRows() - 1, storm.centerRow + storm.radius);
            int minC = Math.max(0, storm.centerCol - storm.radius);
            int maxC = Math.min(world.getCols() - 1, storm.centerCol + storm.radius);

            for (int r = minR; r <= maxR; r++) {
                for (int c = minC; c <= maxC; c++) {
                    if (storm.affects(r, c)) {
                        Cell cell = world.getCell(r, c);
                        int current = cell.getStormSpeedReduction();
                        cell.setStormSpeedReduction(Math.max(current, storm.speedReduction));
                    }
                }
            }
        }
    }

    // ========== Accident Management ==========

    private void checkAccidents(long currentTick, List<? extends BaseVehicle> vehicles) {
        // Check pairs of nearby vehicles for accidents (#22)
        List<? extends BaseVehicle> moving = vehicles.stream()
            .filter(v -> v.getState() == com.multiagent.agents.VehicleState.MOVING)
            .toList();

        for (int i = 0; i < moving.size(); i++) {
            for (int j = i + 1; j < moving.size(); j++) {
                BaseVehicle v1 = moving.get(i);
                BaseVehicle v2 = moving.get(j);

                // Check if in Moore neighborhood (adjacent including diagonals)
                int dr = Math.abs(v1.getRow() - v2.getRow());
                int dc = Math.abs(v1.getCol() - v2.getCol());

                if (dr <= 1 && dc <= 1 && (dr + dc > 0)) {
                    // Check accident probability
                    if (random.nextDouble() < config.accidentProbability) {
                        v1.triggerAccident(currentTick);
                        v2.triggerAccident(currentTick);
                        totalAccidents++;
                        logger.fine(String.format("Accident between %s and %s at tick %d",
                            v1, v2, currentTick));
                    }
                }
            }
        }
    }

    // ========== Getters ==========

    public List<Storm> getActiveStorms() { return activeStorms; }
    public int getTotalStormsCreated() { return totalStormsCreated; }
    public int getTotalBreakdowns() { return totalBreakdowns; }
    public int getTotalAccidents() { return totalAccidents; }

    public void recordBreakdown() { totalBreakdowns++; }
}
