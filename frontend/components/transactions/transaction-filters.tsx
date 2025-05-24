"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Calendar } from "@/components/ui/calendar"
import { CalendarIcon, Filter, Search } from "lucide-react"
import { format } from "date-fns"
import { cn } from "@/lib/utils"
import { Checkbox } from "@/components/ui/checkbox"

export function TransactionFilters() {
  const [date, setDate] = useState<Date>()
  const [showFilters, setShowFilters] = useState(false)

  return (
    <div className="space-y-4">
      <div className="flex flex-col space-y-2 md:flex-row md:items-center md:justify-between md:space-y-0">
        <div className="flex items-center space-x-2">
          <div className="relative w-full md:w-80">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search transactions..." className="pl-8" />
          </div>
          <Button variant="outline" size="icon" onClick={() => setShowFilters(!showFilters)}>
            <Filter className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex items-center space-x-2">
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant={"outline"}
                className={cn("w-[240px] justify-start text-left font-normal", !date && "text-muted-foreground")}
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {date ? format(date, "PPP") : "Pick a date"}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="end">
              <Calendar mode="single" selected={date} onSelect={setDate} initialFocus />
            </PopoverContent>
          </Popover>
          <Button>Apply Filters</Button>
        </div>
      </div>

      {showFilters && (
        <div className="grid gap-4 rounded-lg border p-4 md:grid-cols-4">
          <div className="space-y-2">
            <Label htmlFor="account">Account</Label>
            <Select>
              <SelectTrigger id="account">
                <SelectValue placeholder="All accounts" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All accounts</SelectItem>
                <SelectItem value="ACC-4521">ACC-4521</SelectItem>
                <SelectItem value="ACC-7832">ACC-7832</SelectItem>
                <SelectItem value="ACC-2341">ACC-2341</SelectItem>
                <SelectItem value="ACC-6543">ACC-6543</SelectItem>
                <SelectItem value="ACC-9876">ACC-9876</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="costCenter">Cost Center</Label>
            <Select>
              <SelectTrigger id="costCenter">
                <SelectValue placeholder="All cost centers" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All cost centers</SelectItem>
                <SelectItem value="CC-001">CC-001</SelectItem>
                <SelectItem value="CC-002">CC-002</SelectItem>
                <SelectItem value="CC-003">CC-003</SelectItem>
                <SelectItem value="CC-004">CC-004</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="company">Company</Label>
            <Select>
              <SelectTrigger id="company">
                <SelectValue placeholder="All companies" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All companies</SelectItem>
                <SelectItem value="Acme Corp">Acme Corp</SelectItem>
                <SelectItem value="Globex Inc">Globex Inc</SelectItem>
                <SelectItem value="Initech">Initech</SelectItem>
                <SelectItem value="Massive Dynamic">Massive Dynamic</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="anomalyStatus">Anomaly Status</Label>
            <div className="flex items-center space-x-2 pt-2">
              <Checkbox id="anomalous" />
              <label
                htmlFor="anomalous"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Anomalous
              </label>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox id="normal" />
              <label
                htmlFor="normal"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Normal
              </label>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
