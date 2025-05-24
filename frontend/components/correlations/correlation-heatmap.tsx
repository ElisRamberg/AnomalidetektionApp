"use client"

import { useEffect, useRef } from "react"
import * as d3 from "d3"

// Sample correlation data
const correlationData = [
  ["ACC-4521", "ACC-7832", "ACC-2341", "ACC-6543", "ACC-9876"],
  [
    [1.0, 0.7, 0.3, 0.2, 0.8],
    [0.7, 1.0, 0.5, 0.4, 0.6],
    [0.3, 0.5, 1.0, 0.9, 0.1],
    [0.2, 0.4, 0.9, 1.0, 0.3],
    [0.8, 0.6, 0.1, 0.3, 1.0],
  ],
]

export function CorrelationHeatmap() {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!svgRef.current) return

    const accounts = correlationData[0] as string[]
    const correlations = correlationData[1] as number[][]

    const margin = { top: 50, right: 50, bottom: 50, left: 50 }
    const width = 600 - margin.left - margin.right
    const height = 600 - margin.top - margin.bottom

    // Clear previous SVG content
    d3.select(svgRef.current).selectAll("*").remove()

    const svg = d3
      .select(svgRef.current)
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`)

    // Create scales
    const x = d3.scaleBand().range([0, width]).domain(accounts).padding(0.05)
    const y = d3.scaleBand().range([0, height]).domain(accounts).padding(0.05)

    // Color scale
    const colorScale = d3.scaleLinear<string>().domain([-1, 0, 1]).range(["#2c7bb6", "#ffffbf", "#d7191c"])

    // Create the heatmap cells
    svg
      .selectAll()
      .data(accounts.flatMap((row, i) => accounts.map((col, j) => ({ row, col, value: correlations[i][j] }))))
      .join("rect")
      .attr("x", (d) => x(d.col) || 0)
      .attr("y", (d) => y(d.row) || 0)
      .attr("width", x.bandwidth())
      .attr("height", y.bandwidth())
      .style("fill", (d) => colorScale(d.value))
      .style("stroke", "white")
      .style("stroke-width", 1)

    // Add text to cells
    svg
      .selectAll()
      .data(accounts.flatMap((row, i) => accounts.map((col, j) => ({ row, col, value: correlations[i][j] }))))
      .join("text")
      .attr("x", (d) => (x(d.col) || 0) + x.bandwidth() / 2)
      .attr("y", (d) => (y(d.row) || 0) + y.bandwidth() / 2)
      .attr("text-anchor", "middle")
      .attr("dominant-baseline", "middle")
      .text((d) => d.value.toFixed(2))
      .style("font-size", "12px")
      .style("fill", (d) => (d.value > 0.5 || d.value < -0.5 ? "white" : "black"))

    // Add X axis labels
    svg
      .selectAll()
      .data(accounts)
      .join("text")
      .attr("x", (d) => (x(d) || 0) + x.bandwidth() / 2)
      .attr("y", -10)
      .attr("text-anchor", "middle")
      .style("font-size", "12px")
      .text((d) => d)

    // Add Y axis labels
    svg
      .selectAll()
      .data(accounts)
      .join("text")
      .attr("x", -10)
      .attr("y", (d) => (y(d) || 0) + y.bandwidth() / 2)
      .attr("text-anchor", "end")
      .attr("dominant-baseline", "middle")
      .style("font-size", "12px")
      .text((d) => d)

    // Add title
    svg
      .append("text")
      .attr("x", width / 2)
      .attr("y", -30)
      .attr("text-anchor", "middle")
      .style("font-size", "16px")
      .style("font-weight", "bold")
      .text("Account Correlation Matrix")
  }, [])

  return (
    <div className="flex justify-center overflow-auto">
      <svg ref={svgRef} className="min-w-[600px]"></svg>
    </div>
  )
}
