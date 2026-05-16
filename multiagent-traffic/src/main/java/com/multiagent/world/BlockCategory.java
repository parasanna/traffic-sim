package com.multiagent.world;

/**
 * Categories of building blocks as defined in the specification.
 * Each block represents a city zone with specific characteristics.
 */
public enum BlockCategory {
    /** A - Κατοικίες (Residential) */
    RESIDENTIAL("Κατοικίες", "A"),
    /** B - Γραφεία (Office) */
    OFFICE("Γραφεία", "B"),
    /** C - Αγορές (Market) */
    MARKET("Αγορές", "C"),
    /** D - Αναψυχή (Leisure) */
    LEISURE("Αναψυχή", "D"),
    /** E - Άλλο (Other) */
    OTHER("Άλλο", "E");

    public final String greekName;
    public final String code;

    BlockCategory(String greekName, String code) {
        this.greekName = greekName;
        this.code = code;
    }

    /**
     * Whether this block type consumes food.
     * All blocks consume food as people use them.
     */
    public boolean consumesFood() {
        return this != OTHER;
    }

    /**
     * Whether this block type produces pollution.
     * All blocks produce pollution.
     */
    public boolean producesPollution() {
        return true;
    }

    /**
     * Food consumption multiplier for this block type.
     */
    public double foodConsumptionMultiplier() {
        return switch (this) {
            case RESIDENTIAL -> 1.0;
            case OFFICE -> 0.8;
            case MARKET -> 1.5;
            case LEISURE -> 1.2;
            case OTHER -> 0.3;
        };
    }

    /**
     * Pollution production multiplier for this block type.
     */
    public double pollutionMultiplier() {
        return switch (this) {
            case RESIDENTIAL -> 1.0;
            case OFFICE -> 0.7;
            case MARKET -> 1.3;
            case LEISURE -> 0.9;
            case OTHER -> 0.5;
        };
    }
}
