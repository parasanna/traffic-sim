package com.multiagent.world;

/**
 * Direction of movement on the grid.
 * European convention: drive on the right side.
 */
public enum Direction {
    NORTH(0, -1),  // Up (row decreases)
    SOUTH(0, 1),   // Down (row increases)
    EAST(1, 0),    // Right (col increases)
    WEST(-1, 0);   // Left (col decreases)

    public final int dc; // column delta
    public final int dr; // row delta

    Direction(int dc, int dr) {
        this.dc = dc;
        this.dr = dr;
    }

    /**
     * Returns the opposite direction.
     */
    public Direction opposite() {
        return switch (this) {
            case NORTH -> SOUTH;
            case SOUTH -> NORTH;
            case EAST -> WEST;
            case WEST -> EAST;
        };
    }

    /**
     * Returns the direction rotated 90° clockwise (right turn).
     */
    public Direction turnRight() {
        return switch (this) {
            case NORTH -> EAST;
            case EAST -> SOUTH;
            case SOUTH -> WEST;
            case WEST -> NORTH;
        };
    }

    /**
     * Returns the direction rotated 90° counter-clockwise (left turn).
     */
    public Direction turnLeft() {
        return switch (this) {
            case NORTH -> WEST;
            case WEST -> SOUTH;
            case SOUTH -> EAST;
            case EAST -> NORTH;
        };
    }

    /**
     * Check if this direction is horizontal.
     */
    public boolean isHorizontal() {
        return this == EAST || this == WEST;
    }

    /**
     * Check if this direction is vertical.
     */
    public boolean isVertical() {
        return this == NORTH || this == SOUTH;
    }
}
