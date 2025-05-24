"use client"

import { useState } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

// Define the transaction data type
type Transaction = {
  id: string
  timestamp: string
  accountNumber: string
  transactionId: string
  costCenter: string
  company: string
  amount: number
  currency: string
  isAnomalous: boolean
  anomalyScore: number
}

// Sample transaction data
const transactions: Transaction[] = [
  {
    id: "1",
    timestamp: "2024-05-23T14:32:21",
    accountNumber: "ACC-4521",
    transactionId: "TXN-001",
    costCenter: "CC-001",
    company: "Acme Corp",
    amount: 15420,
    currency: "USD",
    isAnomalous: true,
    anomalyScore: 0.95,
  },
  {
    id: "2",
    timestamp: "2024-05-23T13:15:45",
    accountNumber: "ACC-7832",
    transactionId: "TXN-002",
    costCenter: "CC-003",
    company: "Globex Inc",
    amount: 8750,
    currency: "USD",
    isAnomalous: true,
    anomalyScore: 0.87,
  },
  {
    id: "3",
    timestamp: "2024-05-23T12:48:33",
    accountNumber: "ACC-2341",
    transactionId: "TXN-003",
    costCenter: "CC-002",
    company: "Initech",
    amount: 22100,
    currency: "USD",
    isAnomalous: true,
    anomalyScore: 0.92,
  },
  {
    id: "4",
    timestamp: "2024-05-23T11:27:19",
    accountNumber: "ACC-6543",
    transactionId: "TXN-004",
    costCenter: "CC-001",
    company: "Acme Corp",
    amount: 5320,
    currency: "USD",
    isAnomalous: false,
    anomalyScore: 0.32,
  },
  {
    id: "5",
    timestamp: "2024-05-23T10:15:02",
    accountNumber: "ACC-9876",
    transactionId: "TXN-005",
    costCenter: "CC-004",
    company: "Massive Dynamic",
    amount: 12750,
    currency: "USD",
    isAnomalous: false,
    anomalyScore: 0.28,
  },
  {
    id: "6",
    timestamp: "2024-05-23T09:42:57",
    accountNumber: "ACC-3456",
    transactionId: "TXN-006",
    costCenter: "CC-002",
    company: "Initech",
    amount: 7890,
    currency: "USD",
    isAnomalous: false,
    anomalyScore: 0.15,
  },
  {
    id: "7",
    timestamp: "2024-05-23T08:30:41",
    accountNumber: "ACC-7832",
    transactionId: "TXN-007",
    costCenter: "CC-003",
    company: "Globex Inc",
    amount: 18500,
    currency: "USD",
    isAnomalous: true,
    anomalyScore: 0.89,
  },
  {
    id: "8",
    timestamp: "2024-05-22T17:25:18",
    accountNumber: "ACC-4521",
    transactionId: "TXN-008",
    costCenter: "CC-001",
    company: "Acme Corp",
    amount: 9650,
    currency: "USD",
    isAnomalous: false,
    anomalyScore: 0.42,
  },
  {
    id: "9",
    timestamp: "2024-05-22T16:14:33",
    accountNumber: "ACC-9876",
    transactionId: "TXN-009",
    costCenter: "CC-004",
    company: "Massive Dynamic",
    amount: 31200,
    currency: "USD",
    isAnomalous: true,
    anomalyScore: 0.96,
  },
  {
    id: "10",
    timestamp: "2024-05-22T15:03:27",
    accountNumber: "ACC-2341",
    transactionId: "TXN-010",
    costCenter: "CC-002",
    company: "Initech",
    amount: 4780,
    currency: "USD",
    isAnomalous: false,
    anomalyScore: 0.21,
  },
]

// Define the columns for the table
const columns: ColumnDef<Transaction>[] = [
  {
    accessorKey: "transactionId",
    header: "Transaction ID",
    cell: ({ row }) => <div className="font-medium">{row.getValue("transactionId")}</div>,
  },
  {
    accessorKey: "timestamp",
    header: "Date & Time",
    cell: ({ row }) => {
      const timestamp = new Date(row.getValue("timestamp"))
      return <div>{timestamp.toLocaleString()}</div>
    },
  },
  {
    accessorKey: "accountNumber",
    header: "Account",
    cell: ({ row }) => <div>{row.getValue("accountNumber")}</div>,
  },
  {
    accessorKey: "costCenter",
    header: "Cost Center",
    cell: ({ row }) => <div>{row.getValue("costCenter")}</div>,
  },
  {
    accessorKey: "company",
    header: "Company",
    cell: ({ row }) => <div>{row.getValue("company")}</div>,
  },
  {
    accessorKey: "amount",
    header: "Amount",
    cell: ({ row }) => {
      const amount = Number.parseFloat(row.getValue("amount"))
      const formatted = new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: row.original.currency,
      }).format(amount)
      return <div className="text-right font-medium">{formatted}</div>
    },
  },
  {
    accessorKey: "isAnomalous",
    header: "Status",
    cell: ({ row }) => {
      const isAnomalous = row.getValue("isAnomalous")
      return <Badge variant={isAnomalous ? "destructive" : "secondary"}>{isAnomalous ? "Anomalous" : "Normal"}</Badge>
    },
  },
  {
    accessorKey: "anomalyScore",
    header: "Anomaly Score",
    cell: ({ row }) => {
      const score = Number.parseFloat(row.getValue("anomalyScore"))
      return (
        <div className="flex items-center">
          <div
            className="h-2 w-full rounded-full bg-secondary"
            style={{
              position: "relative",
            }}
          >
            <div
              className="absolute top-0 left-0 h-2 rounded-full bg-destructive"
              style={{
                width: `${score * 100}%`,
              }}
            />
          </div>
          <span className="ml-2 text-xs">{(score * 100).toFixed(0)}%</span>
        </div>
      )
    },
  },
]

export function TransactionsTable() {
  const [sorting, setSorting] = useState<SortingState>([])

  const table = useReactTable({
    data: transactions,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    state: {
      sorting,
    },
  })

  return (
    <div className="space-y-4">
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead key={header.id}>
                      {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                    </TableHead>
                  )
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                  className={row.original.isAnomalous ? "bg-destructive/5" : ""}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-end space-x-2">
        <Button variant="outline" size="sm" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>
          Previous
        </Button>
        <Button variant="outline" size="sm" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>
          Next
        </Button>
      </div>
    </div>
  )
}
