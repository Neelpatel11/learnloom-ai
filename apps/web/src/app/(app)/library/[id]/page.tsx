import { GroupView } from "@/components/group-view";

export const metadata = { title: "Study Group · LearnLoom AI" };

export default async function GroupPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <GroupView groupId={encodeURIComponent(id)} />;
}
