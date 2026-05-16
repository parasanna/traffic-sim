package com.multiagent.agents;

/** Vehicle types matching the specification */
public enum VehicleType {
    RESIDENT,       // Κάτοικοι (P1) - internal traffic
    TRANSIENT,      // Διερχόμενοι (P2) - transit traffic
    FOOD_TRUCK,     // Εφοδιασμός (M) - supply fleet
    GARBAGE_TRUCK   // Συλλογή (N) - collection fleet
}
