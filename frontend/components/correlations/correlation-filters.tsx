"use client"

import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

export function CorrelationFilters() {
  return (
    <div className="space-y-4 rounded-lg border p-4">
      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="accountType">Account Type</Label>
          <Select>
            <SelectTrigger id="accountType">
              <SelectValue placeholder="All account types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All account types</SelectItem>
              <SelectItem value="receivables">Receivables</SelectItem>
              <SelectItem value="payables">Payables</SelectItem>
              <SelectItem value="expenses">Expenses</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="correlationTimeRange">Time Range</Label>
          <Select>
            <SelectTrigger id="correlationTimeRange">
              <SelectValue placeholder="Last 30 days" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7days">Last 7 days</SelectItem>
              <SelectItem value="30days">Last 30 days</SelectItem>
              <SelectItem value="90days">Last 90 days</SelectItem>
              <SelectItem value="1year">Last year</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-end space-x-2">
          <Button>Apply Filters</Button>
          <Button variant="outline">Reset</Button>
        </div>
      </div>
    </div>
  )
}
