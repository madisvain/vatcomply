import { sql } from "drizzle-orm";
import { sqliteTable, text, integer } from "drizzle-orm/sqlite-core";

export const rates = sqliteTable("rates", {
  date: integer("date", { mode: "timestamp" }).primaryKey(),
  rates: text("rates", { mode: "json" }).notNull(),
});
