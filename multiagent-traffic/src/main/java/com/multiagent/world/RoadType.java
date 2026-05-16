package com.multiagent.world;

/**
 * Road types as defined in the specification.
 * 
 * A1, A2: Avenues (λεωφόροι) - blue color, 2 lanes per direction,
 *         enter and exit the region.
 * B1-B3: Local roads (τοπικοί δρόμοι) - brown color,
 *         single lane per direction.
 * C1-C6: One-way streets (μονόδρομοι) - dark gray color,
 *         single lane.
 */
public enum RoadType {
    /** Avenue - 2 lanes per direction, enters/exits region (blue) */
    AVENUE(2, true, false),
    /** Local road - 1 lane per direction (brown) */
    LOCAL(1, true, false),
    /** One-way street - 1 lane, single direction (dark gray) */
    ONE_WAY(1, false, true);

    /** Number of lanes per direction */
    public final int lanesPerDirection;
    /** Whether this road type is bidirectional */
    public final boolean bidirectional;
    /** Whether this road type is one-way */
    public final boolean oneWay;

    RoadType(int lanesPerDirection, boolean bidirectional, boolean oneWay) {
        this.lanesPerDirection = lanesPerDirection;
        this.bidirectional = bidirectional;
        this.oneWay = oneWay;
    }

    /**
     * Total width of the road in cells (including all lanes + sidewalks).
     * Avenue: 2 lanes * 2 directions + 2 sidewalks = 6
     * Local:  1 lane * 2 directions + 2 sidewalks = 4
     * One-way: 1 lane + 2 sidewalks = 3
     */
    public int totalWidth() {
        if (oneWay) {
            return lanesPerDirection + 2; // 1 lane + 2 sidewalks = 3
        }
        return lanesPerDirection * 2 + 2; // lanes both dirs + 2 sidewalks
    }

    /**
     * Number of actual road lanes (excluding sidewalks).
     */
    public int totalLanes() {
        if (oneWay) return lanesPerDirection;
        return lanesPerDirection * 2;
    }
}
