"""
Graph Visualization Module

Provides endpoints and static files for visualizing the knowledge graph.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from app.data.memory.graph.query import get_graph_query
from app.data.memory.graph.models import GraphNode, GraphEdge

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph-visualization"])


@router.get("/visualize")
async def visualize_graph():
    """Serve the graph visualization HTML page."""
    html_path = Path(__file__).parent / "static" / "graph.html"
    
    if html_path.exists():
        return FileResponse(html_path, media_type="text/html")
    
    raise HTTPException(status_code=404, detail="Visualization not available")


@router.get("/data")
async def get_graph_data(
    node_type: Optional[str] = None,
    gmif_type: Optional[str] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    """Get graph data in D3-compatible format."""
    try:
        from app.data.memory.graph.models import GraphNode, GraphEdge
        from app.database.session import get_db_session
        from sqlalchemy import select
        
        nodes = []
        edges = []
        
        async with get_db_session() as session:
            # Get nodes
            node_query = select(GraphNode).limit(limit)
            if node_type:
                node_query = node_query.where(GraphNode.node_type == node_type)
            if gmif_type:
                node_query = node_query.where(GraphNode.gmif_type == gmif_type)
            
            result = await session.execute(node_query)
            db_nodes = result.scalars().all()
            
            for n in db_nodes:
                nodes.append({
                    "id": str(n.id),
                    "label": n.label,
                    "type": n.node_type,
                    "gmif": n.gmif_type,
                    "external_id": n.external_id,
                })
            
            # Get edges
            node_ids = [n.id for n in db_nodes]
            if node_ids:
                edge_result = await session.execute(
                    select(GraphEdge).where(
                        GraphEdge.source_id.in_(node_ids),
                        GraphEdge.target_id.in_(node_ids),
                    )
                )
                db_edges = edge_result.scalars().all()
                
                for e in db_edges:
                    edges.append({
                        "source": str(e.source_id),
                        "target": str(e.target_id),
                        "type": e.relation_type,
                    })
        
        return {
            "nodes": nodes,
            "links": edges,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
            }
        }
    except Exception as e:
        logger.error(f"Failed to get graph data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/heatmap")
async def get_gmif_heatmap() -> Dict[str, Any]:
    """Get GMIF type distribution as heatmap data."""
    try:
        query = get_graph_query()
        summary = await query.get_gmif_summary()
        
        heatmap_data = []
        for gmif_type, count in summary.get("by_gmif", {}).items():
            heatmap_data.append({
                "type": gmif_type,
                "count": count,
                "intensity": min(count / 100, 1.0),
            })
        
        return {"heatmap": heatmap_data}
    except Exception as e:
        logger.error(f"Failed to get heatmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline-data/{entity_external_id}")
async def get_timeline_data(entity_external_id: str) -> Dict[str, Any]:
    """Get timeline data for visualization."""
    try:
        query = get_graph_query()
        timeline = await query.timeline(entity_external_id)
        
        return {
            "entity": entity_external_id,
            "events": [
                {
                    "date": event.get("timestamp"),
                    "type": event.get("node", {}).get("type"),
                    "label": event.get("node", {}).get("label"),
                    "gmif": event.get("node", {}).get("gmif"),
                }
                for event in timeline
            ],
        }
    except Exception as e:
        logger.error(f"Failed to get timeline data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def create_static_files():
    """Create static HTML files for visualization."""
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    
    html_content = """<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PT Tax Intelligence - Knowledge Graph</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f1419; color: #e7e9ea; min-height: 100vh;
        }
        header {
            background: #1d9bf0; padding: 1rem 2rem; color: white;
            display: flex; justify-content: space-between; align-items: center;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 1rem; }
        .grid { display: grid; grid-template-columns: 1fr 300px; gap: 1rem; }
        #graph { 
            background: #15202b; border-radius: 12px; height: 600px; 
            border: 1px solid #38444d; overflow: hidden;
        }
        .sidebar { display: flex; flex-direction: column; gap: 1rem; }
        .card {
            background: #15202b; border-radius: 12px; padding: 1rem;
            border: 1px solid #38444d;
        }
        .card h3 { color: #1d9bf0; margin-bottom: 0.5rem; font-size: 0.9rem; }
        .stat { display: flex; justify-content: space-between; padding: 0.25rem 0; }
        .stat-value { color: #1d9bf0; font-weight: bold; }
        .legend { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }
        .legend-item { 
            display: flex; align-items: center; gap: 0.25rem; font-size: 0.75rem;
        }
        .dot { width: 10px; height: 10px; border-radius: 50%; }
        .controls { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
        button {
            background: #1d9bf0; color: white; border: none; padding: 0.5rem 1rem;
            border-radius: 20px; cursor: pointer; font-size: 0.85rem;
        }
        button:hover { background: #1a8cd8; }
        .node { cursor: pointer; }
        .link { stroke: #38444d; stroke-opacity: 0.6; }
        .tooltip {
            position: absolute; background: #273340; padding: 0.5rem;
            border-radius: 8px; font-size: 0.8rem; pointer-events: none;
            border: 1px solid #38444d;
        }
    </style>
</head>
<body>
    <header>
        <h1>Knowledge Graph - PT Tax Intelligence</h1>
        <span>Epistemic Memory Layer</span>
    </header>
    <div class="container">
        <div class="controls">
            <button onclick="loadGraph()">Refresh</button>
            <button onclick="toggleLayout()">Toggle Layout</button>
            <button onclick="showStats()">Stats</button>
        </div>
        <div class="grid">
            <div id="graph"></div>
            <div class="sidebar">
                <div class="card">
                    <h3>Nodes</h3>
                    <div id="node-stats"></div>
                </div>
                <div class="card">
                    <h3>GMIF Classification</h3>
                    <div id="gmif-legend" class="legend"></div>
                </div>
                <div class="card">
                    <h3>Actions</h3>
                    <button onclick="loadHeatmap()" style="width:100%;margin-top:0.5rem">Show Heatmap</button>
                </div>
            </div>
        </div>
    </div>
    <script>
        const colors = {
            decision: '#f97316',
            entity: '#22c55e',
            legal: '#3b82f6',
            assumption: '#a855f7',
            risk: '#ef4444',
            M1: '#22c55e', M2: '#3b82f6', M3: '#a855f7',
            M4: '#f97316', M5: '#eab308', M6: '#ec4899', M7: '#6b7280'
        };
        
        let svg, simulation, graphData;
        
        async function loadGraph() {
            const response = await fetch('/graph/data');
            graphData = await response.json();
            renderGraph(graphData);
            renderStats(graphData);
            renderLegend();
        }
        
        function renderGraph(data) {
            const container = document.getElementById('graph');
            container.innerHTML = '';
            const width = container.clientWidth;
            const height = container.clientHeight;
            
            svg = d3.select('#graph')
                .append('svg')
                .attr('width', width)
                .attr('height', height);
            
            const g = svg.append('g');
            
            simulation = d3.forceSimulation(data.nodes)
                .force('link', d3.forceLink(data.links).id(d => d.id).distance(80))
                .force('charge', d3.forceManyBody().strength(-200))
                .force('center', d3.forceCenter(width/2, height/2))
                .force('collision', d3.forceCollide().radius(30));
            
            const link = g.selectAll('.link')
                .data(data.links)
                .enter().append('line')
                .attr('class', 'link')
                .attr('stroke-width', 1.5);
            
            const node = g.selectAll('.node')
                .data(data.nodes)
                .enter().append('circle')
                .attr('class', 'node')
                .attr('r', d => d.type === 'decision' ? 12 : 8)
                .attr('fill', d => colors[d.gmif] || colors[d.type] || '#666')
                .call(drag(simulation));
            
            node.append('title').text(d => d.label);
            
            const labels = g.selectAll('.label')
                .data(data.nodes)
                .enter().append('text')
                .text(d => d.label.substring(0, 20))
                .attr('font-size', '10px')
                .attr('fill', '#888')
                .attr('dx', 15)
                .attr('dy', 4);
            
            simulation.on('tick', () => {
                link
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);
                node
                    .attr('cx', d => d.x)
                    .attr('cy', d => d.y);
                labels
                    .attr('x', d => d.x)
                    .attr('y', d => d.y);
            });
        }
        
        function drag(simulation) {
            function dragstarted(event) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            }
            function dragged(event) {
                event.subject.fx = event.x;
                event.subject.fy = event.y;
            }
            function dragended(event) {
                if (!event.active) simulation.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            }
            return d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended);
        }
        
        function renderStats(data) {
            const stats = data.stats;
            document.getElementById('node-stats').innerHTML = `
                <div class="stat"><span>Nodes</span><span class="stat-value">${stats.node_count}</span></div>
                <div class="stat"><span>Edges</span><span class="stat-value">${stats.edge_count}</span></div>
            `;
        }
        
        function renderLegend() {
            const legend = document.getElementById('gmif-legend');
            const items = ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7'];
            legend.innerHTML = items.map(m => 
                `<div class="legend-item"><span class="dot" style="background:${colors[m]}"></span>${m}</div>`
            ).join('');
        }
        
        async function loadHeatmap() {
            const response = await fetch('/graph/heatmap');
            const data = await response.json();
            alert('GMIF Distribution: ' + JSON.stringify(data.heatmap, null, 2));
        }
        
        function showStats() {
            alert('Graph loaded with ' + graphData.stats.node_count + ' nodes and ' + graphData.stats.edge_count + ' edges');
        }
        
        function toggleLayout() {
            if (simulation) {
                simulation.force('charge', simulation.force('charge').strength() > 0 ? -50 : -200);
                simulation.alpha(0.3).restart();
            }
        }
        
        loadGraph();
    </script>
</body>
</html>
"""
    
    with open(static_dir / "graph.html", "w") as f:
        f.write(html_content)
    
    logger.info(f"Created static files in {static_dir}")


create_static_files()