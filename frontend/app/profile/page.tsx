import { redirect } from "next/navigation";

/** The old "Your interests" page now lives in the dashboard. */
export default function Profile() {
  redirect("/dashboard");
}
