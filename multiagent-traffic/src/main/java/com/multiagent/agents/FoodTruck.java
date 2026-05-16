package com.multiagent.agents;

import com.multiagent.config.SimulationConfig;
import com.multiagent.world.*;

/**
 * Food Truck (Εφοδιασμός, M).
 * Enters via Avenue, delivers food to blocks that need it.
 * Capacity: M1 = 50 units (#9).
 */
public class FoodTruck extends BaseVehicle {

    private double currentLoad;
    private final double maxCapacity;
    private BuildingBlock targetBlock;

    public FoodTruck(GridWorld world, SimulationConfig config) {
        super(VehicleType.FOOD_TRUCK, world, config);
        this.maxCapacity = config.supplyCapacity;
        this.currentLoad = maxCapacity; // Start full
    }

    public boolean spawn(long currentTick) {
        int[] entry = world.getRandomEntry();
        if (entry == null) return false;
        Cell entryCell = world.getCell(entry[0], entry[1]);
        if (entryCell == null || entryCell.isOccupied()) return false;

        placeAt(entry[0], entry[1]);
        currentLoad = maxCapacity;
        state = VehicleState.MOVING;
        tripStartTick = currentTick;
        findNextDeliveryTarget(currentTick);
        return true;
    }

    @Override
    public void decide(long currentTick, int timeZone) {
        if (state == VehicleState.IDLE && currentLoad > 0) {
            findNextDeliveryTarget(currentTick);
        } else if (currentLoad <= 0) {
            // Empty - exit the grid to reload
            exitGrid(currentTick);
        }
    }

    private void findNextDeliveryTarget(long currentTick) {
        // Find a block that needs food
        BuildingBlock best = null;
        double lowestFood = 1.0;

        for (BuildingBlock block : world.getBlocks()) {
            if (block.needsFood() && block.getFoodPercentage() < lowestFood) {
                if (!block.getEntryExitPoints().isEmpty()) {
                    lowestFood = block.getFoodPercentage();
                    best = block;
                }
            }
        }

        if (best == null) {
            // No blocks need food, pick random
            best = world.getRandomBlock(BlockCategory.MARKET);
            if (best == null) best = world.getRandomBlock(BlockCategory.RESIDENTIAL);
        }

        if (best != null && !best.getEntryExitPoints().isEmpty()) {
            targetBlock = best;
            int[] entry = best.getEntryExitPoints().get(
                random.nextInt(best.getEntryExitPoints().size()));
            if (planPath(entry[0], entry[1])) {
                state = VehicleState.MOVING;
            }
        }
    }

    private void exitGrid(long currentTick) {
        int[] exit = world.getRandomExit();
        if (exit != null && planPath(exit[0], exit[1])) {
            state = VehicleState.MOVING;
            targetBlock = null;
        }
    }

    @Override
    protected void onPathComplete(long currentTick) {
        if (targetBlock != null && currentLoad > 0) {
            // Start servicing (delivering food)
            state = VehicleState.SERVICING;
            immobilizedUntil = (int)(currentTick + targetBlock.getServiceDuration());
        } else {
            recordTrip(currentTick);
            removeFromGrid();
        }
    }

    @Override
    protected void onServiceComplete(long currentTick) {
        if (targetBlock != null) {
            double delivered = targetBlock.deliverFood(currentLoad);
            currentLoad -= delivered;
        }
        recordTrip(currentTick);
        state = VehicleState.IDLE;
        targetBlock = null;
    }

    public double getCurrentLoad() { return currentLoad; }
    public double getMaxCapacity() { return maxCapacity; }
}
