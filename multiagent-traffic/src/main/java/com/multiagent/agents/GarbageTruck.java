package com.multiagent.agents;

import com.multiagent.config.SimulationConfig;
import com.multiagent.world.*;

/**
 * Garbage Truck (Συλλογή, N).
 * Enters via Avenue, collects pollution from blocks.
 * Capacity: N1 = 250 units (#11).
 */
public class GarbageTruck extends BaseVehicle {

    private double currentLoad;
    private final double maxCapacity;
    private BuildingBlock targetBlock;

    public GarbageTruck(GridWorld world, SimulationConfig config) {
        super(VehicleType.GARBAGE_TRUCK, world, config);
        this.maxCapacity = config.collectionCapacity;
        this.currentLoad = 0; // Start empty
    }

    public boolean spawn(long currentTick) {
        int[] entry = world.getRandomEntry();
        if (entry == null) return false;
        Cell entryCell = world.getCell(entry[0], entry[1]);
        if (entryCell == null || entryCell.isOccupied()) return false;

        placeAt(entry[0], entry[1]);
        currentLoad = 0;
        state = VehicleState.MOVING;
        tripStartTick = currentTick;
        findNextCollectionTarget(currentTick);
        return true;
    }

    @Override
    public void decide(long currentTick, int timeZone) {
        if (state == VehicleState.IDLE) {
            if (currentLoad >= maxCapacity * 0.9) {
                exitGrid(currentTick);
            } else {
                findNextCollectionTarget(currentTick);
            }
        }
    }

    private void findNextCollectionTarget(long currentTick) {
        BuildingBlock best = null;
        double highestPollution = 0;

        for (BuildingBlock block : world.getBlocks()) {
            if (block.needsCollection() && block.getPollutionPercentage() > highestPollution) {
                if (!block.getEntryExitPoints().isEmpty()) {
                    highestPollution = block.getPollutionPercentage();
                    best = block;
                }
            }
        }

        if (best == null) {
            // No urgent blocks, pick any with pollution
            for (BuildingBlock block : world.getBlocks()) {
                if (block.getPollutionLevel() > 0 && !block.getEntryExitPoints().isEmpty()) {
                    best = block;
                    break;
                }
            }
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
        if (targetBlock != null && currentLoad < maxCapacity) {
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
            double space = maxCapacity - currentLoad;
            double collected = targetBlock.collectPollution(space);
            currentLoad += collected;
        }
        recordTrip(currentTick);
        state = VehicleState.IDLE;
        targetBlock = null;
    }

    public double getCurrentLoad() { return currentLoad; }
    public double getMaxCapacity() { return maxCapacity; }
}
