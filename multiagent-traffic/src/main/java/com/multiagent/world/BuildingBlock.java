package com.multiagent.world;

import java.util.ArrayList;
import java.util.List;

/**
 * Represents a building block (Τετράγωνο) in the city grid.
 * Each block has a category (A-E), area, and resource tracking.
 */
public class BuildingBlock {
    /** Block identifier */
    public final String id;

    /** Block category */
    public final BlockCategory category;

    /** All cells belonging to this block */
    private final List<int[]> cells = new ArrayList<>();

    /** Entry/exit points for this block (cells adjacent to roads) */
    private final List<int[]> entryExitPoints = new ArrayList<>();

    /** Current food level (units of "FOOD") */
    private double foodLevel;

    /** Current pollution level (units of "POLLUTION") */
    private double pollutionLevel;

    /** Maximum food storage = F * area */
    private double maxFood;

    /** Maximum pollution storage = P * area */
    private double maxPollution;

    public BuildingBlock(String id, BlockCategory category) {
        this.id = id;
        this.category = category;
    }

    // ========== Cell Management ==========

    public void addCell(int row, int col) {
        cells.add(new int[]{row, col});
    }

    public List<int[]> getCells() { return cells; }

    public int getArea() { return cells.size(); }

    // ========== Entry/Exit Points ==========

    public void addEntryExitPoint(int row, int col) {
        entryExitPoints.add(new int[]{row, col});
    }

    public List<int[]> getEntryExitPoints() { return entryExitPoints; }

    // ========== Resource Management ==========

    /**
     * Initialize resource levels based on block area and config factors.
     * @param foodFactor F (food storage factor, #25)
     * @param pollutionFactor P (pollution storage factor, #28)
     */
    public void initializeResources(double foodFactor, double pollutionFactor) {
        int area = getArea();
        this.maxFood = foodFactor * area;
        this.maxPollution = pollutionFactor * area;
        this.foodLevel = maxFood * 0.8; // Start at 80% food
        this.pollutionLevel = 0; // Start clean
    }

    /**
     * Consume food at this block.
     * @param amount Amount of food to consume
     * @return Actual amount consumed (may be less if not enough food)
     */
    public double consumeFood(double amount) {
        double consumed = Math.min(amount, foodLevel);
        foodLevel -= consumed;
        return consumed;
    }

    /**
     * Deliver food to this block.
     * @param amount Amount of food to deliver
     * @return Actual amount accepted (may be less if storage is full)
     */
    public double deliverFood(double amount) {
        double space = maxFood - foodLevel;
        double accepted = Math.min(amount, space);
        foodLevel += accepted;
        return accepted;
    }

    /**
     * Produce pollution at this block.
     * @param amount Amount of pollution produced
     */
    public void producePollution(double amount) {
        pollutionLevel = Math.min(pollutionLevel + amount, maxPollution);
    }

    /**
     * Collect pollution from this block.
     * @param capacity Maximum amount to collect
     * @return Actual amount collected
     */
    public double collectPollution(double capacity) {
        double collected = Math.min(capacity, pollutionLevel);
        pollutionLevel -= collected;
        return collected;
    }

    // ========== Getters ==========

    public double getFoodLevel() { return foodLevel; }
    public double getPollutionLevel() { return pollutionLevel; }
    public double getMaxFood() { return maxFood; }
    public double getMaxPollution() { return maxPollution; }

    /**
     * Food level as a percentage (0.0 to 1.0).
     */
    public double getFoodPercentage() {
        return maxFood > 0 ? foodLevel / maxFood : 0;
    }

    /**
     * Pollution level as a percentage (0.0 to 1.0).
     */
    public double getPollutionPercentage() {
        return maxPollution > 0 ? pollutionLevel / maxPollution : 0;
    }

    /**
     * Whether this block needs food delivery (below 30% capacity).
     */
    public boolean needsFood() {
        return getFoodPercentage() < 0.3;
    }

    /**
     * Whether this block needs pollution collection (above 70% capacity).
     */
    public boolean needsCollection() {
        return getPollutionPercentage() > 0.7;
    }

    /**
     * Service duration = Area / 4 ticks (#21).
     */
    public int getServiceDuration() {
        return Math.max(1, getArea() / 4);
    }

    @Override
    public String toString() {
        return String.format("Block{id=%s, cat=%s, area=%d, food=%.1f/%.1f, poll=%.1f/%.1f}",
            id, category.code, getArea(), foodLevel, maxFood, pollutionLevel, maxPollution);
    }
}
