"use client"

import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export function GroupFilters() {
  return (
    <div className="space-y-4 rounded-lg border p-4">
      <Tabs defaultValue="accounts">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="accounts">Accounts</TabsTrigger>
          <TabsTrigger value="costCenters">Cost Centers</TabsTrigger>
        </TabsList>
        <TabsContent value="accounts" className="space-y-4 pt-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="accountGroup">Account Group</Label>
              <Select>
                <SelectTrigger id="accountGroup">
                  <SelectValue placeholder="All account groups" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All account groups</SelectItem>
                  <SelectItem value="receivables">Receivables</SelectItem>
                  <SelectItem value="payables">Payables</SelectItem>
                  <SelectItem value="expenses">Expenses</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="timeRange">Time Range</Label>
              <Select>
                <SelectTrigger id="timeRange">
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
        </TabsContent>
        <TabsContent value="costCenters" className="space-y-4 pt-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="costCenterGroup">Cost Center Group</Label>
              <Select>
                <SelectTrigger id="costCenterGroup">
                  <SelectValue placeholder="All cost center groups" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All cost center groups</SelectItem>
                  <SelectItem value="operations">Operations</SelectItem>
                  <SelectItem value="marketing">Marketing</SelectItem>
                  <SelectItem value="it">IT</SelectItem>
                  <SelectItem value="finance">Finance</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="timeRangeCost">Time Range</Label>
              <Select>
                <SelectTrigger id="timeRangeCost">
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
        </TabsContent>
      </Tabs>
    </div>
  )
}
