package com.multiagent.world;

import com.multiagent.config.SimulationConfig;
import java.util.*;
import java.util.logging.Logger;

/**
 * Generates building blocks (Τετράγωνα) on the grid world.
 * Identifies empty regions between roads and assigns categories A-E.
 */
public class BlockGenerator {
    private static final Logger logger = Logger.getLogger(BlockGenerator.class.getName());
    private final GridWorld world;
    private final SimulationConfig config;
    private final Random random;
    private int blockCount = 0;

    public BlockGenerator(GridWorld world, SimulationConfig config, Random random) {
        this.world = world;
        this.config = config;
        this.random = random;
    }

    public void generate() {
        int rows = world.getRows();
        int cols = world.getCols();
        boolean[][] visited = new boolean[rows][cols];

        // Find connected components of EMPTY cells (these become blocks)
        for (int r = 1; r < rows - 1; r++) {
            for (int c = 1; c < cols - 1; c++) {
                Cell cell = world.getCell(r, c);
                if (cell.getType() == CellType.EMPTY && !visited[r][c]) {
                    List<int[]> region = floodFill(r, c, visited);
                    if (region.size() >= 4) { // Min block size
                        createBlock(region);
                    }
                }
            }
        }

        // Initialize resources for all blocks
        for (BuildingBlock block : world.getBlocks()) {
            block.initializeResources(config.foodStorageFactor, config.pollutionStorageFactor);
        }

        logger.info(String.format("Generated %d blocks", world.getBlocks().size()));
        for (BlockCategory cat : BlockCategory.values()) {
            long count = world.getBlocksByCategory(cat).size();
            if (count > 0) logger.info(String.format("  %s (%s): %d", cat.code, cat.greekName, count));
        }
    }

    private List<int[]> floodFill(int startR, int startC, boolean[][] visited) {
        List<int[]> region = new ArrayList<>();
        Queue<int[]> queue = new LinkedList<>();
        queue.add(new int[]{startR, startC});
        visited[startR][startC] = true;

        while (!queue.isEmpty()) {
            int[] pos = queue.poll();
            region.add(pos);
            for (Direction d : Direction.values()) {
                int nr = pos[0] + d.dr;
                int nc = pos[1] + d.dc;
                if (world.inBounds(nr, nc) && !visited[nr][nc]) {
                    Cell neighbor = world.getCell(nr, nc);
                    if (neighbor.getType() == CellType.EMPTY) {
                        visited[nr][nc] = true;
                        queue.add(new int[]{nr, nc});
                    }
                }
            }
        }
        return region;
    }

    private void createBlock(List<int[]> region) {
        blockCount++;
        BlockCategory category = assignCategory(blockCount);
        String id = category.code + blockCount;
        BuildingBlock block = new BuildingBlock(id, category);

        for (int[] pos : region) {
            block.addCell(pos[0], pos[1]);
            Cell cell = world.getCell(pos[0], pos[1]);
            cell.setType(CellType.BUILDING);
            cell.setBlock(block);
        }

        // Find entry/exit points (block cells adjacent to road cells)
        findEntryExitPoints(block);
        world.addBlock(block);
    }

    private void findEntryExitPoints(BuildingBlock block) {
        for (int[] pos : block.getCells()) {
            for (Direction d : Direction.values()) {
                int nr = pos[0] + d.dr;
                int nc = pos[1] + d.dc;
                if (world.inBounds(nr, nc)) {
                    Cell neighbor = world.getCell(nr, nc);
                    if (neighbor.isRoadCell()) {
                        block.addEntryExitPoint(nr, nc);
                        neighbor.setBlockEntryExit(true);
                        break; // One entry per cell is enough
                    }
                }
            }
        }
        // Ensure at least one entry point
        if (block.getEntryExitPoints().isEmpty() && !block.getCells().isEmpty()) {
            int[] first = block.getCells().get(0);
            Cell nearest = world.findNearestRoadCell(first[0], first[1]);
            if (nearest != null) {
                block.addEntryExitPoint(nearest.row, nearest.col);
            }
        }
    }

    private BlockCategory assignCategory(int index) {
        BlockCategory[] categories = BlockCategory.values();
        // Distribute evenly with some randomness
        int base = (index - 1) % categories.length;
        // Add randomness: 30% chance to shift category
        if (random.nextDouble() < 0.3) {
            base = random.nextInt(categories.length);
        }
        return categories[base];
    }
}
