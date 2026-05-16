package com.multiagent.agents;

/** Vehicle states */
public enum VehicleState {
    IDLE,           // Parked / waiting
    MOVING,         // Moving on road
    SERVICING,      // Delivering food or collecting waste
    BROKEN_DOWN,    // Mechanical failure (#19/#20)
    IN_ACCIDENT,    // Accident (#22/#23)
    ENTERING,       // Entering the grid
    EXITING,        // Leaving the grid
    COMPLETED       // Trip completed / removed
}
