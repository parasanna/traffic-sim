package com.multiagent.world;

import com.multiagent.config.SimulationConfig;

import java.util.*;
import java.util.logging.Logger;

/**
 * The Grid World: represents the entire simulation space.
 * A 2D grid of cells containing roads, buildings, sidewalks, etc.
 */
public class GridWorld {
    private static final Logger logger = Logger.getLogger(GridWorld.class.getName());

    private final SimulationConfig config;
    private final int rows;
    private final int cols;
    private final Cell[][] grid;

    /** All roads in the world */
    private final List<Road> roads = new ArrayList<>();

    /** All building blocks in the world */
    private final List<BuildingBlock> blocks = new ArrayList<>();

    /** Border entry points (where vehicles enter from outside) */
    private final List<int[]> borderEntries = new ArrayList<>();

    /** Border exit points (where vehicles leave) */
    private final List<int[]> borderExits = new ArrayList<>();

    /** Random number generator */
    private final Random random;

    public GridWorld(SimulationConfig config, long seed) {
        this.config = config;
        this.rows = config.gridRows;
        this.cols = config.gridCols;
        this.random = new Random(seed);

        // Initialize grid
        grid = new Cell[rows][cols];
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                grid[r][c] = new Cell(r, c);
            }
        }

        // Set border walls (perimeter - light gray)
        for (int r = 0; r < rows; r++) {
            grid[r][0].setType(CellType.WALL);
            grid[r][cols - 1].setType(CellType.WALL);
        }
        for (int c = 0; c < cols; c++) {
            grid[0][c].setType(CellType.WALL);
            grid[rows - 1][c].setType(CellType.WALL);
        }

        logger.info(String.format("GridWorld initialized: %dx%d (%d cells)", rows, cols, rows * cols));
    }

    /**
     * Generate the complete world: roads, blocks, resources.
     */
    public void generate() {
        // Step 1: Generate road network
        RoadNetworkGenerator roadGen = new RoadNetworkGenerator(this, config, random);
        roadGen.generate();

        // Step 2: Generate building blocks
        BlockGenerator blockGen = new BlockGenerator(this, config, random);
        blockGen.generate();

        // Step 3: Fill remaining empty cells as free space (lime green)
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (grid[r][c].getType() == CellType.EMPTY) {
                    grid[r][c].setType(CellType.FREE_SPACE);
                }
            }
        }

        logger.info(String.format("World generated: %d roads, %d blocks, %d entries, %d exits",
            roads.size(), blocks.size(), borderEntries.size(), borderExits.size()));
    }

    // ========== Cell Access ==========

    public Cell getCell(int row, int col) {
        if (row < 0 || row >= rows || col < 0 || col >= cols) return null;
        return grid[row][col];
    }

    public boolean inBounds(int row, int col) {
        return row >= 0 && row < rows && col >= 0 && col < cols;
    }

    /**
     * Get neighboring cells (4-connected, no diagonals).
     */
    public List<Cell> getNeighbors(int row, int col) {
        List<Cell> neighbors = new ArrayList<>(4);
        for (Direction d : Direction.values()) {
            int nr = row + d.dr;
            int nc = col + d.dc;
            if (inBounds(nr, nc)) {
                neighbors.add(grid[nr][nc]);
            }
        }
        return neighbors;
    }

    /**
     * Get the direction from (r1,c1) to (r2,c2). Must be adjacent.
     */
    public Direction getDirection(int r1, int c1, int r2, int c2) {
        int dr = r2 - r1;
        int dc = c2 - c1;
        for (Direction d : Direction.values()) {
            if (d.dr == dr && d.dc == dc) return d;
        }
        return null;
    }

    // ========== Road Management ==========

    public void addRoad(Road road) {
        roads.add(road);
    }

    public List<Road> getRoads() { return roads; }

    public List<Road> getRoadsByType(RoadType type) {
        return roads.stream().filter(r -> r.type == type).toList();
    }

    // ========== Block Management ==========

    public void addBlock(BuildingBlock block) {
        blocks.add(block);
    }

    public List<BuildingBlock> getBlocks() { return blocks; }

    public List<BuildingBlock> getBlocksByCategory(BlockCategory category) {
        return blocks.stream().filter(b -> b.category == category).toList();
    }

    // ========== Border Entry/Exit ==========

    public void addBorderEntry(int row, int col) {
        borderEntries.add(new int[]{row, col});
    }

    public void addBorderExit(int row, int col) {
        borderExits.add(new int[]{row, col});
    }

    public List<int[]> getBorderEntries() { return borderEntries; }
    public List<int[]> getBorderExits() { return borderExits; }

    /**
     * Get a random border entry point.
     */
    public int[] getRandomEntry() {
        if (borderEntries.isEmpty()) return null;
        return borderEntries.get(random.nextInt(borderEntries.size()));
    }

    /**
     * Get a random border exit point.
     */
    public int[] getRandomExit() {
        if (borderExits.isEmpty()) return null;
        return borderExits.get(random.nextInt(borderExits.size()));
    }

    // ========== Traffic Light Management ==========

    /**
     * Update traffic lights based on the current tick.
     * Lights alternate every 30 ticks (90 seconds).
     */
    public void updateTrafficLights(long tick) {
        int cycleLength = 30; // 30 ticks per phase
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                Cell cell = grid[r][c];
                if (cell.getType() == CellType.TRAFFIC_LIGHT || cell.getType() == CellType.INTERSECTION) {
                    int phase = cell.getTrafficLightPhase();
                    boolean green = ((tick + phase) / cycleLength) % 2 == 0;
                    cell.setTrafficLightGreen(green);
                }
            }
        }
    }

    // ========== Resource Update ==========

    /**
     * Update food consumption and pollution production for all blocks.
     */
    public void updateResources(long tick) {
        for (BuildingBlock block : blocks) {
            if (block.category.consumesFood()) {
                // FCR: 1 unit per 50 ticks per cell (#24)
                double foodConsumed = block.getArea() * config.foodConsumptionRate
                    * block.category.foodConsumptionMultiplier();
                block.consumeFood(foodConsumed);
            }

            if (block.category.producesPollution()) {
                // PGR: 1 unit per 100 ticks per cell (#27)
                double pollutionProduced = block.getArea() * config.pollutionRate
                    * block.category.pollutionMultiplier();
                block.producePollution(pollutionProduced);
            }
        }
    }

    // ========== Accessors ==========

    public int getRows() { return rows; }
    public int getCols() { return cols; }
    public SimulationConfig getConfig() { return config; }
    public Random getRandom() { return random; }

    /**
     * Get all cells within perception radius R of a position.
     */
    public List<Cell> getPerceivedCells(int row, int col) {
        int r = config.perceptionRadius;
        List<Cell> perceived = new ArrayList<>();
        for (int dr = -r; dr <= r; dr++) {
            for (int dc = -r; dc <= r; dc++) {
                int nr = row + dr;
                int nc = col + dc;
                if (inBounds(nr, nc)) {
                    perceived.add(grid[nr][nc]);
                }
            }
        }
        return perceived;
    }

    /**
     * Get a random block of the given category.
     */
    public BuildingBlock getRandomBlock(BlockCategory category) {
        List<BuildingBlock> categoryBlocks = getBlocksByCategory(category);
        if (categoryBlocks.isEmpty()) {
            // Fallback: get any block
            if (blocks.isEmpty()) return null;
            return blocks.get(random.nextInt(blocks.size()));
        }
        return categoryBlocks.get(random.nextInt(categoryBlocks.size()));
    }

    /**
     * Get the nearest block entry point to a given position.
     */
    public int[] getNearestBlockEntry(int row, int col, BuildingBlock block) {
        int[] nearest = null;
        int minDist = Integer.MAX_VALUE;
        for (int[] pt : block.getEntryExitPoints()) {
            int dist = Math.abs(pt[0] - row) + Math.abs(pt[1] - col);
            if (dist < minDist) {
                minDist = dist;
                nearest = pt;
            }
        }
        return nearest;
    }

    /**
     * Find the nearest road cell to a given position.
     */
    public Cell findNearestRoadCell(int row, int col) {
        int searchRadius = 20;
        Cell nearest = null;
        int minDist = Integer.MAX_VALUE;
        for (int dr = -searchRadius; dr <= searchRadius; dr++) {
            for (int dc = -searchRadius; dc <= searchRadius; dc++) {
                int nr = row + dr;
                int nc = col + dc;
                if (inBounds(nr, nc)) {
                    Cell cell = grid[nr][nc];
                    if (cell.isRoadCell() && !cell.isOccupied()) {
                        int dist = Math.abs(dr) + Math.abs(dc);
                        if (dist < minDist) {
                            minDist = dist;
                            nearest = cell;
                        }
                    }
                }
            }
        }
        return nearest;
    }
}
