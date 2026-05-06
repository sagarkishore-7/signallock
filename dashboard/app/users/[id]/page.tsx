import { UserDetailClient } from "@/components/UserDetailClient";

interface PageProps {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ count?: string; seed?: string }>;
}

export default async function UserPage({ params, searchParams }: PageProps) {
  const { id } = await params;
  const search = await searchParams;
  const rosterCount = Number(search.count ?? 20);
  const rosterSeed = Number(search.seed ?? 1);

  return (
    <UserDetailClient
      employeeId={id}
      rosterCount={rosterCount}
      rosterSeed={rosterSeed}
    />
  );
}
