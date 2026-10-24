import { redirect } from "next/navigation";

// The founder opens this instead of the Monday spreadsheet. Send them straight there.
export default function Home(): never {
  redirect("/monday");
}
