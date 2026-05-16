package com.multiagent.world;

/**
 * Enumeration of cell types in the grid world.
 */
public enum CellType {
    /** Empty cell - available for block/road placement */
    EMPTY,
    /** Wall - border of the grid world (perimeter, light gray) */
    WALL,
    /** Road cell - part of a road lane */
    ROAD,
    /** Sidewalk (πεζοδρόμιο, petrol color) */
    SIDEWALK,
    /** Intersection (διασταύρωση, dark yellow) */
    INTERSECTION,
    /** Traffic light (σηματοδότης, purple) */
    TRAFFIC_LIGHT,
    /** Building block cell - part of a block/building */
    BUILDING,
    /** Entry/exit point (red dots) */
    ENTRY_EXIT,
    /** Free space (ελεύθερος χώρος, lime green) */
    FREE_SPACE
}
