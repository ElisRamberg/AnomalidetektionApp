"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Bell, Search, User } from "lucide-react"

export function Header() {
  return (
    <header className="flex items-center justify-between h-16 px-4 border-b bg-background">
      <div className="flex items-center flex-1 space-x-4">
        <div className="relative w-64">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search transactions..." className="pl-8" />
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <Button variant="ghost" size="sm" className="relative">
          <Bell className="h-4 w-4" />
          <Badge className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 text-xs">3</Badge>
        </Button>
        <Button variant="ghost" size="sm">
          <User className="h-4 w-4" />
        </Button>
      </div>
    </header>
  )
}
