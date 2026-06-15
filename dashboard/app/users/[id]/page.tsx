import { UserDetailClient } from "@/components/UserDetailClient";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function UserPage({ params }: PageProps) {
  const { id } = await params;
  return <UserDetailClient subjectId={decodeURIComponent(id)} />;
}
