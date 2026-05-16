package com.multiagent.agents;

import com.multiagent.config.SimulationConfig;
import com.multiagent.world.*;

/**
 * Resident vehicle (Κάτοικοι, P1).
 * Follows daily activity patterns: HOME → WORK → MARKET → LEISURE → HOME.
 * Decisions based on time zones.
 */
public class ResidentVehicle extends BaseVehicle {

    private BuildingBlock homeBlock;
    private BuildingBlock currentTarget;
    private ActivityType activity = ActivityType.HOME;

    public enum ActivityType {
        HOME, WORK, SHOPPING, LEISURE
    }

    public ResidentVehicle(GridWorld world, SimulationConfig config) {
        super(VehicleType.RESIDENT, world, config);
    }

    /**
     * Assign a home block to this resident.
     */
    public void setHomeBlock(BuildingBlock home) {
        this.homeBlock = home;
        // Place at a road cell near home
        if (!home.getEntryExitPoints().isEmpty()) {
            int[] entry = home.getEntryExitPoints().get(0);
            placeAt(entry[0], entry[1]);
        }
    }

    @Override
    public void decide(long currentTick, int timeZone) {
        if (state == VehicleState.BROKEN_DOWN || state == VehicleState.IN_ACCIDENT
            || state == VehicleState.SERVICING) return;

        ActivityType desired = getDesiredActivity(timeZone);
        if (desired != activity && state != VehicleState.MOVING) {
            activity = desired;
            navigateToActivity(currentTick);
        }
    }

    private ActivityType getDesiredActivity(int timeZone) {
        return switch (timeZone) {
            case 0, 1, 7 -> ActivityType.HOME;      // Night/early morning
            case 2, 3 -> ActivityType.WORK;          // Morning → work
            case 4 -> ActivityType.SHOPPING;         // Afternoon → market
            case 5, 6 -> {
                yield random.nextDouble() < 0.5 ?
                    ActivityType.LEISURE : ActivityType.HOME;
            }
            default -> ActivityType.HOME;
        };
    }

    private void navigateToActivity(long currentTick) {
        BlockCategory targetCat = switch (activity) {
            case HOME -> BlockCategory.RESIDENTIAL;
            case WORK -> BlockCategory.OFFICE;
            case SHOPPING -> BlockCategory.MARKET;
            case LEISURE -> BlockCategory.LEISURE;
        };

        BuildingBlock target = world.getRandomBlock(targetCat);
        if (target == null || target.getEntryExitPoints().isEmpty()) return;

        currentTarget = target;
        int[] entry = target.getEntryExitPoints().get(
            random.nextInt(target.getEntryExitPoints().size()));

        tripStartTick = currentTick;
        tripStartRow = row;
        tripStartCol = col;
        totalDistance = 0;

        if (planPath(entry[0], entry[1])) {
            state = VehicleState.MOVING;
        }
    }

    @Override
    protected void onPathComplete(long currentTick) {
        recordTrip(currentTick);
        state = VehicleState.IDLE;
    }

    @Override
    protected void onServiceComplete(long currentTick) {
        state = VehicleState.IDLE;
    }

    public BuildingBlock getHomeBlock() { return homeBlock; }
    public ActivityType getActivity() { return activity; }
}
