package com.multiagent.agents;

import com.multiagent.config.SimulationConfig;
import com.multiagent.pathfinding.AStarPathfinder;
import com.multiagent.world.*;

import java.util.*;

/**
 * Base class for all vehicle agents in the simulation.
 * Handles movement, pathfinding, breakdowns, accidents, and trip tracking.
 */
public abstract class BaseVehicle {
    private static int nextId = 0;

    public final int id;
    public final VehicleType vehicleType;

    protected VehicleState state = VehicleState.IDLE;
    protected int row, col;            // Current position
    protected int speed;               // Current speed (cells/tick, #31)
    protected int baseSpeed;           // Base speed before storm reduction
    protected List<int[]> path;        // Current planned path
    protected int pathIndex;           // Current position in path
    protected GridWorld world;
    protected SimulationConfig config;
    protected Random random;

    // Immobilization
    protected int immobilizedUntil = 0; // Tick when vehicle can move again

    // Trip tracking
    protected long tripStartTick;
    protected int tripStartRow, tripStartCol;
    protected int totalDistance;        // Manhattan distance traveled
    protected int tripsCompleted;

    // Statistics
    protected long totalTravelTime;
    protected int totalTripDistance;

    public BaseVehicle(VehicleType type, GridWorld world, SimulationConfig config) {
        this.id = nextId++;
        this.vehicleType = type;
        this.world = world;
        this.config = config;
        this.random = world.getRandom();
        this.path = new ArrayList<>();
        this.pathIndex = 0;
    }

    /**
     * Main tick update method. Called every simulation tick.
     */
    public void update(long currentTick) {
        if (state == VehicleState.COMPLETED) return;

        // Check immobilization (breakdown/accident)
        if (state == VehicleState.BROKEN_DOWN || state == VehicleState.IN_ACCIDENT) {
            if (currentTick >= immobilizedUntil) {
                state = VehicleState.MOVING;
            } else {
                return; // Still immobilized
            }
        }

        // Check for servicing completion
        if (state == VehicleState.SERVICING) {
            if (currentTick >= immobilizedUntil) {
                onServiceComplete(currentTick);
            }
            return;
        }

        // Determine speed for this tick
        rollSpeed();

        // Apply storm speed reduction
        Cell currentCell = world.getCell(row, col);
        if (currentCell != null) {
            int reduction = currentCell.getStormSpeedReduction();
            speed = Math.max(0, speed - reduction);
        }

        if (speed <= 0) return; // Can't move

        // Check breakdown probability (#19)
        if (random.nextDouble() < config.breakdownProbability) {
            triggerBreakdown(currentTick);
            return;
        }

        // Move along path
        doMovement(currentTick);
    }

    /**
     * Roll a random speed for this tick (#31: [1,5] cells/tick).
     */
    protected void rollSpeed() {
        baseSpeed = config.minSpeed + random.nextInt(config.maxSpeed - config.minSpeed + 1);
        speed = baseSpeed;
    }

    /**
     * Execute movement along the planned path.
     */
    protected void doMovement(long currentTick) {
        if (path == null || pathIndex >= path.size()) {
            onPathComplete(currentTick);
            return;
        }

        int steps = speed;
        while (steps > 0 && pathIndex < path.size()) {
            int[] next = path.get(pathIndex);
            Cell nextCell = world.getCell(next[0], next[1]);

            if (nextCell == null || !nextCell.isPassable()) {
                // Blocked - try to reroute or wait
                break;
            }

            // Check traffic light
            if (nextCell.getType() == CellType.INTERSECTION && !nextCell.isTrafficLightGreen()) {
                break; // Red light - stop
            }

            // Move to next cell
            Cell current = world.getCell(row, col);
            if (current != null) current.clearOccupant();

            row = next[0];
            col = next[1];
            nextCell.setOccupant(this);
            pathIndex++;
            totalDistance++;
            steps--;
        }
    }

    /**
     * Plan a path to the given target using A*.
     */
    protected boolean planPath(int targetRow, int targetCol) {
        AStarPathfinder pathfinder = new AStarPathfinder(world);
        List<int[]> newPath = pathfinder.findPath(row, col, targetRow, targetCol);
        if (newPath != null && !newPath.isEmpty()) {
            this.path = newPath;
            this.pathIndex = 0;
            return true;
        }
        return false;
    }

    /**
     * Trigger a mechanical breakdown (#19, #20).
     */
    public void triggerBreakdown(long currentTick) {
        state = VehicleState.BROKEN_DOWN;
        immobilizedUntil = (int)(currentTick + config.breakdownDuration);
    }

    /**
     * Trigger an accident (#22, #23).
     */
    public void triggerAccident(long currentTick) {
        state = VehicleState.IN_ACCIDENT;
        immobilizedUntil = (int)(currentTick + config.accidentDuration);
    }

    /**
     * Place this vehicle at the given position.
     */
    public void placeAt(int row, int col) {
        this.row = row;
        this.col = col;
        Cell cell = world.getCell(row, col);
        if (cell != null) cell.setOccupant(this);
    }

    /**
     * Remove this vehicle from the grid.
     */
    public void removeFromGrid() {
        Cell cell = world.getCell(row, col);
        if (cell != null) cell.clearOccupant();
        state = VehicleState.COMPLETED;
    }

    /**
     * Record a completed trip.
     */
    protected void recordTrip(long endTick) {
        long travelTime = endTick - tripStartTick;
        totalTravelTime += travelTime;
        totalTripDistance += totalDistance;
        tripsCompleted++;
        totalDistance = 0;
    }

    // ========== Abstract Methods ==========

    /** Called when the current path is completed */
    protected abstract void onPathComplete(long currentTick);

    /** Called when servicing is completed */
    protected abstract void onServiceComplete(long currentTick);

    /** Decide next action based on current state and time zone */
    public abstract void decide(long currentTick, int timeZone);

    // ========== Getters ==========

    public VehicleState getState() { return state; }
    public int getRow() { return row; }
    public int getCol() { return col; }
    public int getSpeed() { return speed; }
    public int getTripsCompleted() { return tripsCompleted; }
    public long getTotalTravelTime() { return totalTravelTime; }
    public int getTotalTripDistance() { return totalTripDistance; }

    public boolean isActive() {
        return state != VehicleState.COMPLETED && state != VehicleState.IDLE;
    }

    @Override
    public String toString() {
        return String.format("%s#%d(%s@%d,%d)", vehicleType, id, state, row, col);
    }
}
