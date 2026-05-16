package com.multiagent.agents;

import com.multiagent.config.SimulationConfig;
import com.multiagent.world.*;

/**
 * Transient vehicle (Διερχόμενοι, P2).
 * Enters via an Avenue entry, traverses the grid, exits via an Avenue exit.
 * Never parks. Transit traffic.
 */
public class TransientVehicle extends BaseVehicle {

    private int[] exitPoint;

    public TransientVehicle(GridWorld world, SimulationConfig config) {
        super(VehicleType.TRANSIENT, world, config);
    }

    /**
     * Spawn at a random border entry and plan route to a random border exit.
     */
    public boolean spawn(long currentTick) {
        int[] entry = world.getRandomEntry();
        if (entry == null) return false;

        Cell entryCell = world.getCell(entry[0], entry[1]);
        if (entryCell == null || entryCell.isOccupied()) return false;

        placeAt(entry[0], entry[1]);
        state = VehicleState.ENTERING;

        // Pick a random exit point (different from entry)
        exitPoint = world.getRandomExit();
        if (exitPoint == null) return false;

        tripStartTick = currentTick;
        tripStartRow = row;
        tripStartCol = col;
        totalDistance = 0;

        if (planPath(exitPoint[0], exitPoint[1])) {
            state = VehicleState.MOVING;
            return true;
        }

        // Can't find path, remove
        removeFromGrid();
        return false;
    }

    @Override
    public void decide(long currentTick, int timeZone) {
        // Transients just follow their path, no decisions needed
    }

    @Override
    protected void onPathComplete(long currentTick) {
        recordTrip(currentTick);
        removeFromGrid();
    }

    @Override
    protected void onServiceComplete(long currentTick) {
        // Transients don't service
    }

    public int[] getExitPoint() { return exitPoint; }
}
