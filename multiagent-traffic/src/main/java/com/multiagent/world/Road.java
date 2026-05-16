package com.multiagent.world;

import java.util.ArrayList;
import java.util.List;

/**
 * Represents a road in the grid world.
 * Roads have an ID (e.g., "A1", "B2", "C3"), a type, orientation,
 * and a list of cells they occupy.
 */
public class Road {
    /** Road identifier (e.g., "A1", "B2", "C3") */
    public final String id;

    /** Road type */
    public final RoadType type;

    /** Whether this road is horizontal (true) or vertical (false) */
    public final boolean horizontal;

    /** Center line position (row for horizontal, col for vertical) */
    public final int centerLine;

    /** All cells belonging to this road */
    private final List<int[]> cells = new ArrayList<>();

    /** Entry points at the border (for avenues - where vehicles enter the region) */
    private final List<int[]> entryPoints = new ArrayList<>();

    /** Exit points at the border (for avenues - where vehicles exit the region) */
    private final List<int[]> exitPoints = new ArrayList<>();

    /** One-way direction (only for ONE_WAY roads) */
    private Direction oneWayDirection;

    public Road(String id, RoadType type, boolean horizontal, int centerLine) {
        this.id = id;
        this.type = type;
        this.horizontal = horizontal;
        this.centerLine = centerLine;
    }

    // ========== Cell Management ==========

    public void addCell(int row, int col) {
        cells.add(new int[]{row, col});
    }

    public List<int[]> getCells() {
        return cells;
    }

    // ========== Entry/Exit Points ==========

    public void addEntryPoint(int row, int col) {
        entryPoints.add(new int[]{row, col});
    }

    public void addExitPoint(int row, int col) {
        exitPoints.add(new int[]{row, col});
    }

    public List<int[]> getEntryPoints() {
        return entryPoints;
    }

    public List<int[]> getExitPoints() {
        return exitPoints;
    }

    // ========== One-Way Direction ==========

    public Direction getOneWayDirection() { return oneWayDirection; }
    public void setOneWayDirection(Direction dir) { this.oneWayDirection = dir; }

    @Override
    public String toString() {
        return String.format("Road{id=%s, type=%s, %s, center=%d, cells=%d, entries=%d, exits=%d}",
            id, type, horizontal ? "H" : "V", centerLine, cells.size(),
            entryPoints.size(), exitPoints.size());
    }
}
