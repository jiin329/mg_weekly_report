import { useEffect, useState } from "react";
import type { ChatRoom, Message } from "../types";
import {
  ApiError,
  CONNECTION_ERROR,
  createApiClient,
  type ApiClient,
} from "../api/apiClient";
import { createMockFetch } from "../mock/mockBackend";
import { RoomList } from "./RoomList";
import { MessageList } from "./MessageList";
import { MessageBubble } from "./MessageBubble";
import { InputArea } from "./InputArea";
import { GenerateButton } from "./GenerateButton";
import { ReportCard } from "./ReportCard";
import { LoadingIndicator } from "./LoadingIndicator";
import { ConnectionErrorBanner } from "./ConnectionErrorBanner";
import { ThemeToggle } from "./ThemeToggle";
import "./AppShell.css";

export interface AppShellProps {
  apiClient?: ApiClient;
}

export function AppShell({ apiClient }: AppShellProps) {
  const [client] = useState<ApiClient>(
    () =>
      apiClient ??
      createApiClient({
        baseUrl: "http://127.0.0.1:8000",
        fetchFn: createMockFetch(),
      }),
  );

  const [rooms, setRooms] = useState<ChatRoom[]>([]);
  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [connectionError, setConnectionError] = useState(false);

  const selectedRoom = rooms.find((room) => room.id === selectedRoomId) ?? null;
  const hasUserMessages = messages.some((m) => m.sender === "user");

  function handleError(error: unknown) {
    if (error instanceof ApiError && error.code === CONNECTION_ERROR) {
      setConnectionError(true);
    }
  }

  async function loadMessages(roomId: string) {
    try {
      setMessages(await client.listMessages(roomId));
    } catch (error) {
      handleError(error);
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        let list = await client.listRooms();
        if (list.length === 0) {
          await client.createRoom();
          list = await client.listRooms();
        }
        if (cancelled) return;
        setRooms(list);

        const target = pickDefaultRoom(list);
        if (target) {
          setSelectedRoomId(target.id);
          const msgs = await client.listMessages(target.id);
          if (!cancelled) setMessages(msgs);
        }
      } catch (error) {
        if (!cancelled) handleError(error);
      } finally {
        if (!cancelled) setInitialLoading(false);
      }
    }

    init();
    return () => {
      cancelled = true;
    };
  }, [client]);

  async function handleSelectRoom(roomId: string) {
    if (roomId === selectedRoomId) return;
    setSelectedRoomId(roomId);
    await loadMessages(roomId);
  }

  async function handleSend(content: string) {
    if (!selectedRoomId) return;
    try {
      const message = await client.sendMessage(selectedRoomId, content);
      setMessages((prev) => [...prev, message]);
    } catch (error) {
      handleError(error);
    }
  }

  async function handleGenerate() {
    if (!selectedRoomId) return;
    setGenerating(true);
    try {
      const { closedRoomId } = await client.generateReport(selectedRoomId);
      const refreshed = await client.listRooms();
      setRooms(refreshed);
      setSelectedRoomId(closedRoomId);
      await loadMessages(closedRoomId);
    } catch (error) {
      handleError(error);
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="app-shell">
      {connectionError && <ConnectionErrorBanner />}
      <div className="app-shell__body">
        <aside className="app-shell__sidebar">
          <div className="app-shell__sidebar-header">
            <h1 className="app-shell__title">주간보고 채팅</h1>
            <ThemeToggle />
          </div>
          <RoomList
            rooms={rooms}
            selectedRoomId={selectedRoomId}
            onSelectRoom={handleSelectRoom}
          />
        </aside>

        <main className="app-shell__main" aria-label="채팅">
          {initialLoading ? (
            <LoadingIndicator label="불러오는 중..." />
          ) : selectedRoom ? (
            <>
              <MessageList
                messages={messages}
                renderMessage={(m) => <MessageBubble key={m.id} message={m} />}
              />

              {selectedRoom.report && <ReportCard report={selectedRoom.report} />}

              {generating && <LoadingIndicator />}

              <div className="app-shell__actions">
                <GenerateButton
                  roomStatus={selectedRoom.status}
                  hasMessages={hasUserMessages}
                  onGenerate={handleGenerate}
                />
              </div>

              <InputArea
                onSend={handleSend}
                disabled={selectedRoom.status !== "active"}
              />
            </>
          ) : (
            <p className="app-shell__empty">채팅방을 불러올 수 없습니다.</p>
          )}
        </main>
      </div>
    </div>
  );
}

function pickDefaultRoom(rooms: ChatRoom[]): ChatRoom | null {
  const actives = rooms.filter((room) => room.status === "active");
  const pool = actives.length > 0 ? actives : rooms;
  return pool.reduce<ChatRoom | null>(
    (latest, room) =>
      latest === null || room.createdAt > latest.createdAt ? room : latest,
    null,
  );
}
