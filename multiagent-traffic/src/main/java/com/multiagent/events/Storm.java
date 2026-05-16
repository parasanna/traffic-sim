package com.multiagent.events;

/**
 * Represents a storm (Καταιγίδα) in the simulation.
 * Storms reduce vehicle speed within their radius (#15-#18).
 */
public class Storm {
    private static int nextId = 0;

    public final int id;
    public final int centerRow;
    public final int centerCol;
    public final int radius;          // #17: 50-100 cells
    public final long startTick;
    public final long endTick;
    public final int speedReduction;  // #18: -2 cells/tick

    private boolean active = true;

    public Storm(int centerRow, int centerCol, int radius,
                 long startTick, long duration, int speedReduction) {
        this.id = nextId++;
        this.centerRow = centerRow;
        this.centerCol = centerCol;
        this.radius = radius;
        this.startTick = startTick;
        this.endTick = startTick + duration;
        this.speedReduction = speedReduction;
    }

    /**
     * Check if a cell position is within this storm's area.
     */
    public boolean affects(int row, int col) {
        if (!active) return false;
        int dr = row - centerRow;
        int dc = col - centerCol;
        return (dr * dr + dc * dc) <= (radius * radius);
    }

    /**
     * Update storm state.
     */
    public void update(long currentTick) {
        if (currentTick >= endTick) {
            active = false;
        }
    }

    public boolean isActive() { return active; }

    @Override
    public String toString() {
        return String.format("Storm#%d(center=%d,%d, r=%d, %s)",
            id, centerRow, centerCol, radius, active ? "ACTIVE" : "ENDED");
    }
}
