package com.multiagent.metrics;

import com.multiagent.agents.*;
import java.util.*;

/**
 * Collects and computes simulation metrics as defined in the specification.
 * 
 * Metrics:
 * 1. Average transit time - Transient traffic (Διερχόμενοι)
 * 2. Average transit time - Internal traffic (Κάτοικοι)
 * 3. Average transit time per unit length - Transient
 * 4. Average transit time per unit length - Internal
 * 5. Total flow difference - Transient traffic
 */
public class MetricsCollector {

    // Daily data for transit traffic
    private final List<Long> dailyTransitTimes = new ArrayList<>();
    private final List<Integer> dailyTransitDistances = new ArrayList<>();
    private final List<Integer> dailyTransitEntries = new ArrayList<>();
    private final List<Integer> dailyTransitExits = new ArrayList<>();

    // Daily data for internal traffic
    private final List<Long> dailyInternalTimes = new ArrayList<>();
    private final List<Integer> dailyInternalDistances = new ArrayList<>();

    // Current day accumulators
    private long currentDayTransitTime = 0;
    private int currentDayTransitDistance = 0;
    private int currentDayTransitCount = 0;
    private int currentDayEntries = 0;
    private int currentDayExits = 0;

    private long currentDayInternalTime = 0;
    private int currentDayInternalDistance = 0;
    private int currentDayInternalCount = 0;

    private int currentDay = 0;

    /**
     * Record a completed transit trip (Transient vehicle).
     */
    public void recordTransitTrip(long travelTime, int distance) {
        currentDayTransitTime += travelTime;
        currentDayTransitDistance += distance;
        currentDayTransitCount++;
    }

    /**
     * Record a completed internal trip (Resident vehicle).
     */
    public void recordInternalTrip(long travelTime, int distance) {
        currentDayInternalTime += travelTime;
        currentDayInternalDistance += distance;
        currentDayInternalCount++;
    }

    /** Record a transit entry */
    public void recordTransitEntry() { currentDayEntries++; }

    /** Record a transit exit */
    public void recordTransitExit() { currentDayExits++; }

    /**
     * Called when a new day starts. Archives current day data.
     */
    public void onNewDay(int day) {
        if (day > currentDay) {
            // Save daily stats
            dailyTransitTimes.add(currentDayTransitTime);
            dailyTransitDistances.add(currentDayTransitDistance);
            dailyTransitEntries.add(currentDayEntries);
            dailyTransitExits.add(currentDayExits);
            dailyInternalTimes.add(currentDayInternalTime);
            dailyInternalDistances.add(currentDayInternalDistance);

            // Reset
            currentDayTransitTime = 0;
            currentDayTransitDistance = 0;
            currentDayTransitCount = 0;
            currentDayEntries = 0;
            currentDayExits = 0;
            currentDayInternalTime = 0;
            currentDayInternalDistance = 0;
            currentDayInternalCount = 0;
            currentDay = day;
        }
    }

    // ========== Metric Computations ==========

    /** Metric 1: Average transit time for transient traffic */
    public double getAvgTransitTime() {
        long totalTime = dailyTransitTimes.stream().mapToLong(Long::longValue).sum() + currentDayTransitTime;
        int totalCount = dailyTransitTimes.size() + (currentDayTransitCount > 0 ? 1 : 0);
        // Count is number of completed trips overall
        long totalTrips = currentDayTransitCount;
        for (int i = 0; i < dailyTransitTimes.size(); i++) {
            totalTrips += dailyTransitDistances.get(i) > 0 ? 1 : 0; // approximate
        }
        return totalTrips > 0 ? (double) totalTime / Math.max(1, currentDayTransitCount) : 0;
    }

    /** Metric 2: Average transit time for internal traffic */
    public double getAvgInternalTime() {
        long totalTime = dailyInternalTimes.stream().mapToLong(Long::longValue).sum() + currentDayInternalTime;
        int totalCount = currentDayInternalCount;
        return totalCount > 0 ? (double) totalTime / totalCount : 0;
    }

    /** Metric 3: Average transit time per unit length - Transient */
    public double getAvgTransitTimePerLength() {
        return currentDayTransitDistance > 0 ?
            (double) currentDayTransitTime / currentDayTransitDistance : 0;
    }

    /** Metric 4: Average transit time per unit length - Internal */
    public double getAvgInternalTimePerLength() {
        return currentDayInternalDistance > 0 ?
            (double) currentDayInternalTime / currentDayInternalDistance : 0;
    }

    /** Metric 5: Total flow difference for transient traffic */
    public int getFlowDifference() {
        int totalEntries = dailyTransitEntries.stream().mapToInt(Integer::intValue).sum() + currentDayEntries;
        int totalExits = dailyTransitExits.stream().mapToInt(Integer::intValue).sum() + currentDayExits;
        return totalEntries - totalExits;
    }

    /**
     * Get a summary map of all metrics.
     */
    public Map<String, Object> getSummary() {
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("avgTransitTime", String.format("%.2f", getAvgTransitTime()));
        summary.put("avgInternalTime", String.format("%.2f", getAvgInternalTime()));
        summary.put("avgTransitTimePerLength", String.format("%.4f", getAvgTransitTimePerLength()));
        summary.put("avgInternalTimePerLength", String.format("%.4f", getAvgInternalTimePerLength()));
        summary.put("flowDifference", getFlowDifference());
        summary.put("currentDay", currentDay);
        summary.put("dailyTransitTrips", currentDayTransitCount);
        summary.put("dailyInternalTrips", currentDayInternalCount);
        return summary;
    }
}
