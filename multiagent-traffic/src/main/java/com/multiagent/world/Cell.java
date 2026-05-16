package com.multiagent.world;

import com.multiagent.agents.BaseVehicle;

/**
 * Represents a single cell in the grid world.
 * Contains type, road, direction, and occupancy information.
 */
public class Cell {
    /** Position in the grid */
    public final int row;
    public final int col;

    /** Cell type */
    private CellType type = CellType.EMPTY;

    /** Road this cell belongs to (null if not a road cell) */
    private Road road;

    /** Road type for this cell */
    private RoadType roadType;

    /** Lane direction for road cells */
    private Direction laneDirection;

    /** Building block this cell belongs to (null if not a building cell) */
    private BuildingBlock block;

    /** Whether this cell is a border entry point */
    private boolean borderEntry = false;

    /** Whether this cell is a border exit point */
    private boolean borderExit = false;

    /** Whether this cell is a block entry/exit point (red dot) */
    private boolean blockEntryExit = false;

    /** Current occupant vehicle (null if empty) */
    private BaseVehicle occupant;

    /** Traffic light state: true = green, false = red */
    private boolean trafficLightGreen = true;

    /** Traffic light cycle offset (for synchronization) */
    private int trafficLightPhase = 0;

    /** Speed reduction due to storm */
    private int stormSpeedReduction = 0;

    public Cell(int row, int col) {
        this.row = row;
        this.col = col;
    }

    // ========== Getters ==========

    public CellType getType() { return type; }
    public Road getRoad() { return road; }
    public RoadType getRoadType() { return roadType; }
    public Direction getLaneDirection() { return laneDirection; }
    public BuildingBlock getBlock() { return block; }
    public boolean isBorderEntry() { return borderEntry; }
    public boolean isBorderExit() { return borderExit; }
    public boolean isBlockEntryExit() { return blockEntryExit; }
    public BaseVehicle getOccupant() { return occupant; }
    public boolean isTrafficLightGreen() { return trafficLightGreen; }
    public int getTrafficLightPhase() { return trafficLightPhase; }
    public int getStormSpeedReduction() { return stormSpeedReduction; }

    // ========== Setters ==========

    public void setType(CellType type) { this.type = type; }
    public void setRoad(Road road) { this.road = road; }
    public void setRoadType(RoadType roadType) { this.roadType = roadType; }
    public void setLaneDirection(Direction direction) { this.laneDirection = direction; }
    public void setBlock(BuildingBlock block) { this.block = block; }
    public void setBorderEntry(boolean entry) { this.borderEntry = entry; }
    public void setBorderExit(boolean exit) { this.borderExit = exit; }
    public void setBlockEntryExit(boolean entryExit) { this.blockEntryExit = entryExit; }
    public void setTrafficLightGreen(boolean green) { this.trafficLightGreen = green; }
    public void setTrafficLightPhase(int phase) { this.trafficLightPhase = phase; }
    public void setStormSpeedReduction(int reduction) { this.stormSpeedReduction = reduction; }

    /**
     * Set the occupant vehicle. Returns true if successful (cell was empty).
     */
    public boolean setOccupant(BaseVehicle vehicle) {
        if (vehicle != null && this.occupant != null) {
            return false; // Cell already occupied
        }
        this.occupant = vehicle;
        return true;
    }

    /**
     * Remove the current occupant.
     */
    public void clearOccupant() {
        this.occupant = null;
    }

    /**
     * Check if this cell is passable by a vehicle.
     */
    public boolean isPassable() {
        return (type == CellType.ROAD || type == CellType.INTERSECTION ||
                type == CellType.ENTRY_EXIT) && occupant == null;
    }

    /**
     * Check if this cell is a road-type cell (road, intersection, or entry/exit).
     */
    public boolean isRoadCell() {
        return type == CellType.ROAD || type == CellType.INTERSECTION ||
               type == CellType.ENTRY_EXIT || type == CellType.TRAFFIC_LIGHT;
    }

    /**
     * Check if this cell is occupied.
     */
    public boolean isOccupied() {
        return occupant != null;
    }

    /**
     * Get the effective speed reduction at this cell (from storms).
     */
    public int getEffectiveSpeedReduction() {
        return stormSpeedReduction;
    }

    @Override
    public String toString() {
        return String.format("Cell(%d,%d,%s)", row, col, type);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Cell cell = (Cell) o;
        return row == cell.row && col == cell.col;
    }

    @Override
    public int hashCode() {
        return 31 * row + col;
    }
}
