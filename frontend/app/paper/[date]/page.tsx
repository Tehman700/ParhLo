"use client";

import { useParams } from "next/navigation";
import { EditionScreen } from "@/components/paper/EditionScreen";

export default function PastPaper() {
  const { date } = useParams<{ date: string }>();
  return <EditionScreen date={date} />;
}
