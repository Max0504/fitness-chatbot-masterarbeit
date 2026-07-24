const RASA_URL = "http://localhost:5005/webhooks/rest/webhook";

export interface RasaResponse {
  recipient_id: string;
  text?: string;
  image?: string;
  buttons?: { title: string; payload: string }[];
}

export async function sendChatMessage(
  message: string,
  sender?: string
): Promise<RasaResponse[]> {
  const res = await fetch(RASA_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sender: sender ?? "demo_user", message }),
  });
  if (!res.ok) throw new Error(`Rasa request failed: ${res.status}`);
  return res.json();
}
