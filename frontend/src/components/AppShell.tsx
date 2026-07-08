import { useEffect, useState } from "react";
import { ApiError, CONNECTION_ERROR, type ApiClient } from "../api/apiClient";
import { createBackendApiClient } from "../api/backend";
import type { ChatRoom, Message } from "../types";
import "./AppShell.css";
import { ConnectionErrorBanner } from "./ConnectionErrorBanner";
import { GenerateButton } from "./GenerateButton";
import { InputArea } from "./InputArea";
import { LoadingIndicator } from "./LoadingIndicator";
import { MessageBubble } from "./MessageBubble";
import { MessageList } from "./MessageList";
import { ReportCard } from "./ReportCard";
import { RoomList } from "./RoomList";

/**
 * AppShell is the top-level Chat_UI composition (design.md: AppShell).
 *
 * It owns the small amount of state the screen needs (rooms, the selected room,
 * that room's messages, and the loading / connection flags) and wires the leaf
 * components to the apiClient. State lives here — close to where it is used —
 * with plain useState/useEffect; no global store (per frontend steering).
 *
 * Layout: a sidebar (RoomList) beside a flexible main chat area. The layout is
 * responsive via CSS flexbox (see AppShell.css), so it adapts when the
 * Application_Window is resized (Req 2.6) without any JS resize listener.
 *
 * The apiClient is injectable: by default it talks to the REAL loopback backend
 * over local HTTP (task 8.2, Req 10.3). Tests and FE-only development inject a
 * client wired to the in-memory mock backend harness instead.
 */
export interface AppShellProps {
  apiClient?: ApiClient;
}

export function AppShell({ apiClient }: AppShellProps) {
  // Build the client once. Default to the real loopback backend (Req 10.3);
  // callers inject a mock-backed client for standalone/FE-only runs.
  const [client] = useState<ApiClient>(
    () => apiClient ?? createBackendApiClient(),
  );

  const [rooms, setRooms] = useState<ChatRoom[]>([]);
  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [connectionError, setConnectionError] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const selectedRoom = rooms.find((room) => room.id === selectedRoomId) ?? null;
  const hasUserMessages = messages.some((m) => m.sender === "user");

  function handleError(error: unknown) {
    // The "backend unreachable" case gets the connection banner (Req 10.9).
    if (error instanceof ApiError && error.code === CONNECTION_ERROR) {
      setConnectionError(true);
      return;
    }
    // Every other structured error (e.g. LLM_UNAVAILABLE / LLM_TIMEOUT /
    // CONFIG_MISSING during report generation) must be shown to the user;
    // otherwise the action fails silently and nothing appears on screen.
    if (error instanceof ApiError) {
      setErrorMessage(error.message);
      return;
    }
    setErrorMessage("요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.");
  }

  async function loadMessages(roomId: string) {
    try {
      setMessages(await client.listMessages(roomId));
    } catch (error) {
      handleError(error);
    }
  }

  // Initial load: fetch rooms, create one if none exist, then select the most
  // recent active room and load its messages (Req 1.3, 1.4, 7.4).
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
    setErrorMessage(null);
    try {
      const message = await client.sendMessage(selectedRoomId, content);
      setMessages((prev) => [...prev, message]);
    } catch (error) {
      handleError(error);
    }
  }

  async function handleGenerate() {
    if (!selectedRoomId) return;
    setErrorMessage(null);
    setGenerating(true);
    try {
      const { closedRoomId } = await client.generateReport(selectedRoomId);
      const refreshed = await client.listRooms();
      setRooms(refreshed);
      // Show the just-generated report by viewing the now-closed room
      // (read-only, Req 5.4 / 6.5). The new active room appears in the sidebar
      // list (Req 6.4) for the user to continue next week.
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
          <h1 className="app-shell__title">주간보고 채팅</h1>
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

/**
 * Picks the room to show by default: the most recent active room, falling back
 * to the most recent room overall if none are active (Req 7.4).
 */
function pickDefaultRoom(rooms: ChatRoom[]): ChatRoom | null {
  const actives = rooms.filter((room) => room.status === "active");
  const pool = actives.length > 0 ? actives : rooms;
  return pool.reduce<ChatRoom | null>(
    (latest, room) =>
      latest === null || room.createdAt > latest.createdAt ? room : latest,
    null,
  );
}
