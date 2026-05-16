package com.multiagent.pathfinding;

import com.multiagent.world.*;
import java.util.*;

/**
 * A* pathfinding algorithm for the grid world.
 * Supports lane direction constraints, no diagonal movement.
 */
public class AStarPathfinder {
    private final GridWorld world;

    public AStarPathfinder(GridWorld world) {
        this.world = world;
    }

    /**
     * Find the shortest path from start to goal on the road network.
     * @return List of [row,col] positions, or null if no path found.
     */
    public List<int[]> findPath(int startRow, int startCol, int goalRow, int goalCol) {
        if (!world.inBounds(startRow, startCol) || !world.inBounds(goalRow, goalCol)) {
            return null;
        }

        // Priority queue: [f-cost, g-cost, row, col]
        PriorityQueue<int[]> openSet = new PriorityQueue<>(
            Comparator.comparingInt(a -> a[0]));
        Map<Long, Integer> gScore = new HashMap<>();
        Map<Long, long[]> cameFrom = new HashMap<>();
        Set<Long> closedSet = new HashSet<>();

        long startKey = key(startRow, startCol);
        gScore.put(startKey, 0);
        openSet.add(new int[]{heuristic(startRow, startCol, goalRow, goalCol), 0, startRow, startCol});

        int maxIterations = world.getRows() * world.getCols();
        int iterations = 0;

        while (!openSet.isEmpty() && iterations < maxIterations) {
            iterations++;
            int[] current = openSet.poll();
            int curRow = current[2];
            int curCol = current[3];
            long curKey = key(curRow, curCol);

            if (curRow == goalRow && curCol == goalCol) {
                return reconstructPath(cameFrom, curRow, curCol);
            }

            if (closedSet.contains(curKey)) continue;
            closedSet.add(curKey);

            int curG = gScore.getOrDefault(curKey, Integer.MAX_VALUE);
            Cell curCell = world.getCell(curRow, curCol);

            // Explore neighbors (4-connected)
            for (Direction d : Direction.values()) {
                int nr = curRow + d.dr;
                int nc = curCol + d.dc;
                long nKey = key(nr, nc);

                if (!world.inBounds(nr, nc) || closedSet.contains(nKey)) continue;

                Cell neighbor = world.getCell(nr, nc);

                // Check if neighbor is passable
                if (!neighbor.isRoadCell() && neighbor.getType() != CellType.ENTRY_EXIT) continue;

                // Check lane direction compatibility
                Direction laneDir = neighbor.getLaneDirection();
                if (laneDir != null) {
                    // For one-way roads, must follow the lane direction
                    if (neighbor.getRoadType() == RoadType.ONE_WAY && laneDir != d) continue;
                }

                // Movement cost
                int moveCost = 1;
                // Extra cost for occupied cells
                if (neighbor.isOccupied()) moveCost += 5;
                // Extra cost at red lights
                if (neighbor.getType() == CellType.INTERSECTION && !neighbor.isTrafficLightGreen()) {
                    moveCost += 3;
                }

                int tentG = curG + moveCost;
                if (tentG < gScore.getOrDefault(nKey, Integer.MAX_VALUE)) {
                    gScore.put(nKey, tentG);
                    cameFrom.put(nKey, new long[]{curRow, curCol});
                    int f = tentG + heuristic(nr, nc, goalRow, goalCol);
                    openSet.add(new int[]{f, tentG, nr, nc});
                }
            }
        }

        return null; // No path found
    }

    /**
     * Manhattan distance heuristic.
     */
    private int heuristic(int r1, int c1, int r2, int c2) {
        return Math.abs(r1 - r2) + Math.abs(c1 - c2);
    }

    /**
     * Unique key for a grid position.
     */
    private long key(int row, int col) {
        return (long) row * 10000 + col;
    }

    /**
     * Reconstruct the path from cameFrom map.
     */
    private List<int[]> reconstructPath(Map<Long, long[]> cameFrom, int endRow, int endCol) {
        List<int[]> path = new ArrayList<>();
        int r = endRow, c = endCol;
        long k = key(r, c);

        while (cameFrom.containsKey(k)) {
            path.add(new int[]{r, c});
            long[] prev = cameFrom.get(k);
            r = (int) prev[0];
            c = (int) prev[1];
            k = key(r, c);
        }

        Collections.reverse(path);
        return path;
    }
}
