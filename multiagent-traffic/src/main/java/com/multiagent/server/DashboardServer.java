package com.multiagent.server;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.multiagent.agents.*;
import com.multiagent.engine.SimulationEngine;
import com.multiagent.events.Storm;
import com.multiagent.world.*;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.*;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.logging.Logger;

/**
 * HTTP server for the simulation dashboard.
 * Serves the HTML dashboard and provides JSON API for simulation state.
 */
public class DashboardServer {
    private static final Logger logger = Logger.getLogger(DashboardServer.class.getName());
    private final Gson gson = new GsonBuilder().create();

    private HttpServer server;
    private SimulationEngine engine;
    private final int port;

    public DashboardServer(int port) {
        this.port = port;
    }

    public void start(SimulationEngine engine) throws IOException {
        this.engine = engine;
        server = HttpServer.create(new InetSocketAddress(port), 0);

        server.createContext("/", this::serveDashboard);
        server.createContext("/api/state", this::serveState);
        server.createContext("/api/grid", this::serveGrid);
        server.createContext("/api/metrics", this::serveMetrics);

        server.setExecutor(null);
        server.start();
        logger.info("Dashboard server started at http://localhost:" + port);
    }

    public void stop() {
        if (server != null) {
            server.stop(0);
        }
    }

    private void serveDashboard(HttpExchange exchange) throws IOException {
        // Read dashboard.html from resources
        InputStream is = getClass().getResourceAsStream("/dashboard.html");
        String html;
        if (is != null) {
            html = new String(is.readAllBytes(), StandardCharsets.UTF_8);
        } else {
            html = "<html><body><h1>Dashboard not found</h1></body></html>";
        }
        sendResponse(exchange, 200, html, "text/html");
    }

    private void serveState(HttpExchange exchange) throws IOException {
        Map<String, Object> state = new LinkedHashMap<>();
        state.put("tick", engine.getCurrentTick());
        state.put("day", engine.getCurrentDay() + 1);
        state.put("zone", engine.getCurrentZone());
        state.put("zoneLabel", engine.getConfig().getZoneLabel(engine.getCurrentZone()));
        state.put("running", engine.isRunning());

        // Vehicle counts
        Map<String, Integer> counts = new LinkedHashMap<>();
        counts.put("residents", engine.getActiveResidents());
        counts.put("transients", engine.getActiveTransients());
        counts.put("foodTrucks", engine.getActiveFoodTrucks());
        counts.put("garbageTrucks", engine.getActiveGarbageTrucks());
        int total = engine.getActiveResidents() + engine.getActiveTransients()
            + engine.getActiveFoodTrucks() + engine.getActiveGarbageTrucks();
        counts.put("total", total);
        state.put("vehicles", counts);

        // Events
        Map<String, Object> events = new LinkedHashMap<>();
        events.put("activeStorms", engine.getEventManager().getActiveStorms().size());
        events.put("totalStorms", engine.getEventManager().getTotalStormsCreated());
        events.put("totalAccidents", engine.getEventManager().getTotalAccidents());
        events.put("totalBreakdowns", engine.getEventManager().getTotalBreakdowns());
        state.put("events", events);

        // Storm data
        List<Map<String, Object>> storms = new ArrayList<>();
        for (Storm s : engine.getEventManager().getActiveStorms()) {
            Map<String, Object> stormData = new LinkedHashMap<>();
            stormData.put("centerRow", s.centerRow);
            stormData.put("centerCol", s.centerCol);
            stormData.put("radius", s.radius);
            storms.add(stormData);
        }
        state.put("storms", storms);

        // Vehicle positions
        List<Map<String, Object>> vehicleList = new ArrayList<>();
        for (BaseVehicle v : engine.getAllVehicles()) {
            if (v.getState() == VehicleState.COMPLETED) continue;
            Map<String, Object> vData = new LinkedHashMap<>();
            vData.put("id", v.id);
            vData.put("type", v.vehicleType.name());
            vData.put("state", v.getState().name());
            vData.put("row", v.getRow());
            vData.put("col", v.getCol());
            vehicleList.add(vData);
        }
        state.put("vehiclePositions", vehicleList);

        // Metrics
        state.put("metrics", engine.getMetrics().getSummary());

        sendResponse(exchange, 200, gson.toJson(state), "application/json");
    }

    private void serveGrid(HttpExchange exchange) throws IOException {
        GridWorld world = engine.getWorld();
        int rows = world.getRows();
        int cols = world.getCols();

        // Create compact grid representation
        // Each cell encoded as a single character for efficiency
        StringBuilder sb = new StringBuilder();
        Map<String, Object> gridData = new LinkedHashMap<>();
        gridData.put("rows", rows);
        gridData.put("cols", cols);

        // Encode cells as type codes
        int[][] cellTypes = new int[rows][cols];
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                Cell cell = world.getCell(r, c);
                cellTypes[r][c] = cell.getType().ordinal();
            }
        }
        gridData.put("cells", cellTypes);

        // Block data
        List<Map<String, Object>> blockData = new ArrayList<>();
        for (BuildingBlock block : world.getBlocks()) {
            Map<String, Object> bd = new LinkedHashMap<>();
            bd.put("id", block.id);
            bd.put("category", block.category.code);
            bd.put("area", block.getArea());
            bd.put("food", String.format("%.0f", block.getFoodLevel()));
            bd.put("maxFood", String.format("%.0f", block.getMaxFood()));
            bd.put("pollution", String.format("%.0f", block.getPollutionLevel()));
            bd.put("maxPollution", String.format("%.0f", block.getMaxPollution()));
            // Representative position (center of block)
            if (!block.getCells().isEmpty()) {
                int midIdx = block.getCells().size() / 2;
                bd.put("labelRow", block.getCells().get(midIdx)[0]);
                bd.put("labelCol", block.getCells().get(midIdx)[1]);
            }
            blockData.add(bd);
        }
        gridData.put("blocks", blockData);

        // Road data
        List<Map<String, Object>> roadData = new ArrayList<>();
        for (Road road : world.getRoads()) {
            Map<String, Object> rd = new LinkedHashMap<>();
            rd.put("id", road.id);
            rd.put("type", road.type.name());
            rd.put("horizontal", road.horizontal);
            roadData.add(rd);
        }
        gridData.put("roads", roadData);

        sendResponse(exchange, 200, gson.toJson(gridData), "application/json");
    }

    private void serveMetrics(HttpExchange exchange) throws IOException {
        sendResponse(exchange, 200,
            gson.toJson(engine.getMetrics().getSummary()), "application/json");
    }

    private void sendResponse(HttpExchange exchange, int code, String body, String contentType) throws IOException {
        exchange.getResponseHeaders().set("Content-Type", contentType + "; charset=UTF-8");
        exchange.getResponseHeaders().set("Access-Control-Allow-Origin", "*");
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.sendResponseHeaders(code, bytes.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(bytes);
        }
    }
}
