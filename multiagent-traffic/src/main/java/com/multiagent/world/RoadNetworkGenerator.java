package com.multiagent.world;

import com.multiagent.config.SimulationConfig;
import java.util.*;
import java.util.logging.Logger;

/**
 * Generates the road network on the grid world.
 * A1/A2 Avenues, B1-B3 Local roads, C1-C6 One-way streets.
 */
public class RoadNetworkGenerator {
    private static final Logger logger = Logger.getLogger(RoadNetworkGenerator.class.getName());
    private final GridWorld world;
    private final SimulationConfig config;
    private final Random random;
    private int avenueCount = 0, localCount = 0, oneWayCount = 0;

    public RoadNetworkGenerator(GridWorld world, SimulationConfig config, Random random) {
        this.world = world;
        this.config = config;
        this.random = random;
    }

    public void generate() {
        int rows = world.getRows();
        int cols = world.getCols();

        // A1: horizontal avenue at ~40%
        createRoad(RoadType.AVENUE, true, rows * 2 / 5);
        // A2: vertical avenue at ~50%
        createRoad(RoadType.AVENUE, false, cols / 2);
        // B1: horizontal local at ~20%
        createRoad(RoadType.LOCAL, true, rows / 5);
        // B2: vertical local at ~30%
        createRoad(RoadType.LOCAL, false, cols * 3 / 10);
        // B3: horizontal local at ~70%
        createRoad(RoadType.LOCAL, true, rows * 7 / 10);
        // C1-C6: one-way streets
        createRoad(RoadType.ONE_WAY, true, rows * 3 / 10);
        createRoad(RoadType.ONE_WAY, false, cols / 5);
        createRoad(RoadType.ONE_WAY, true, rows * 55 / 100);
        createRoad(RoadType.ONE_WAY, false, cols * 7 / 10);
        createRoad(RoadType.ONE_WAY, true, rows * 85 / 100);
        createRoad(RoadType.ONE_WAY, false, cols * 4 / 5);

        setupIntersections();
        setupBorderEntries();

        logger.info(String.format("Road network: %d avenues, %d local, %d one-way",
            avenueCount, localCount, oneWayCount));
    }

    private void createRoad(RoadType type, boolean horizontal, int centerLine) {
        String id;
        switch (type) {
            case AVENUE -> { avenueCount++; id = "A" + avenueCount; }
            case LOCAL -> { localCount++; id = "B" + localCount; }
            case ONE_WAY -> { oneWayCount++; id = "C" + oneWayCount; }
            default -> id = "?";
        }

        Road road = new Road(id, type, horizontal, centerLine);
        int width = type.totalWidth();
        int halfWidth = width / 2;
        int startOffset = centerLine - halfWidth;

        Direction oneWayDir = null;
        if (type == RoadType.ONE_WAY) {
            if (horizontal) {
                oneWayDir = (oneWayCount % 2 == 0) ? Direction.EAST : Direction.WEST;
            } else {
                oneWayDir = (oneWayCount % 2 == 0) ? Direction.SOUTH : Direction.NORTH;
            }
            road.setOneWayDirection(oneWayDir);
        }

        int rows = world.getRows();
        int cols = world.getCols();

        if (horizontal) {
            for (int c = 0; c < cols; c++) {
                for (int offset = 0; offset < width; offset++) {
                    int r = startOffset + offset;
                    if (!world.inBounds(r, c)) continue;
                    Cell cell = world.getCell(r, c);
                    if (cell.getType() != CellType.EMPTY && cell.getType() != CellType.WALL) continue;
                    if (cell.getType() == CellType.WALL && type != RoadType.AVENUE) continue;

                    if (offset == 0 || offset == width - 1) {
                        cell.setType(CellType.SIDEWALK);
                    } else {
                        cell.setType(CellType.ROAD);
                        cell.setRoad(road);
                        cell.setRoadType(type);
                        if (type == RoadType.ONE_WAY) {
                            cell.setLaneDirection(oneWayDir);
                        } else {
                            int laneIndex = offset - 1;
                            cell.setLaneDirection(laneIndex < type.totalLanes() / 2 ?
                                Direction.EAST : Direction.WEST);
                        }
                        road.addCell(r, c);
                    }
                }
            }
        } else {
            for (int r = 0; r < rows; r++) {
                for (int offset = 0; offset < width; offset++) {
                    int c = startOffset + offset;
                    if (!world.inBounds(r, c)) continue;
                    Cell cell = world.getCell(r, c);
                    if (cell.getType() != CellType.EMPTY && cell.getType() != CellType.WALL) continue;
                    if (cell.getType() == CellType.WALL && type != RoadType.AVENUE) continue;

                    if (offset == 0 || offset == width - 1) {
                        cell.setType(CellType.SIDEWALK);
                    } else {
                        cell.setType(CellType.ROAD);
                        cell.setRoad(road);
                        cell.setRoadType(type);
                        if (type == RoadType.ONE_WAY) {
                            cell.setLaneDirection(oneWayDir);
                        } else {
                            int laneIndex = offset - 1;
                            cell.setLaneDirection(laneIndex < type.totalLanes() / 2 ?
                                Direction.SOUTH : Direction.NORTH);
                        }
                        road.addCell(r, c);
                    }
                }
            }
        }

        world.addRoad(road);
        logger.fine(String.format("Road %s: %s %s @ %d, %d cells",
            id, type, horizontal ? "H" : "V", centerLine, road.getCells().size()));
    }

    private void setupIntersections() {
        int count = 0;
        for (int r = 1; r < world.getRows() - 1; r++) {
            for (int c = 1; c < world.getCols() - 1; c++) {
                Cell cell = world.getCell(r, c);
                if (cell.getType() != CellType.ROAD) continue;

                boolean hasH = false, hasV = false;
                Direction dir = cell.getLaneDirection();
                if (dir != null) {
                    if (dir.isHorizontal()) hasH = true; else hasV = true;
                }
                for (Direction d : Direction.values()) {
                    int nr = r + d.dr, nc = c + d.dc;
                    if (world.inBounds(nr, nc)) {
                        Cell n = world.getCell(nr, nc);
                        if (n.getType() == CellType.ROAD && n.getLaneDirection() != null) {
                            if (n.getLaneDirection().isHorizontal()) hasH = true;
                            else hasV = true;
                        }
                    }
                }
                if (hasH && hasV) {
                    cell.setType(CellType.INTERSECTION);
                    cell.setTrafficLightPhase((r + c) % 4);
                    count++;
                }
            }
        }
        logger.info(count + " intersection cells created");
    }

    private void setupBorderEntries() {
        int rows = world.getRows(), cols = world.getCols();
        for (Road road : world.getRoads()) {
            if (road.type != RoadType.AVENUE) continue;
            for (int[] pos : road.getCells()) {
                int r = pos[0], c = pos[1];
                Cell cell = world.getCell(r, c);
                Direction dir = cell.getLaneDirection();
                if (dir == null) continue;
                boolean atBorder = (r <= 1 || r >= rows - 2 || c <= 1 || c >= cols - 2);
                if (!atBorder) continue;

                if (isInward(r, c, dir, rows, cols)) {
                    cell.setBorderEntry(true);
                    cell.setType(CellType.ENTRY_EXIT);
                    road.addEntryPoint(r, c);
                    world.addBorderEntry(r, c);
                } else {
                    cell.setBorderExit(true);
                    cell.setType(CellType.ENTRY_EXIT);
                    road.addExitPoint(r, c);
                    world.addBorderExit(r, c);
                }
            }
        }
        logger.info(String.format("Border: %d entries, %d exits",
            world.getBorderEntries().size(), world.getBorderExits().size()));
    }

    private boolean isInward(int r, int c, Direction dir, int rows, int cols) {
        if (r <= 1 && dir == Direction.SOUTH) return true;
        if (r >= rows - 2 && dir == Direction.NORTH) return true;
        if (c <= 1 && dir == Direction.EAST) return true;
        if (c >= cols - 2 && dir == Direction.WEST) return true;
        return false;
    }
}
