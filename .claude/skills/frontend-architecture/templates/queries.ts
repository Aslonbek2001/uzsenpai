// entities/order/api/queries.ts — query keys, a query, and an optimistic mutation.
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { get, send } from "@/shared/api/client";
// Types come from the generated OpenAPI schema (make api-types):
// import type { components } from "@/shared/api/generated/schema";
// type Order = components["schemas"]["OrderOut"];
type OrderStatus = "created" | "paid" | "in_progress" | "delivered" | "completed" | "cancelled" | "refunded";
type Order = { id: string; title: string; status: OrderStatus; due_at: string | null };
type Page<T> = { items: T[]; next_cursor: string | null };

export const orderKeys = {
  all: ["orders"] as const,
  list: (cursor: string | null) => [...orderKeys.all, "list", cursor] as const,
  detail: (id: string) => [...orderKeys.all, "detail", id] as const,
};

export function useOrders(cursor: string | null) {
  return useQuery({
    queryKey: orderKeys.list(cursor),
    queryFn: ({ signal }) => get<Page<Order>>(`/orders?cursor=${encodeURIComponent(cursor ?? "")}`, signal),
    placeholderData: keepPreviousData, // no empty flash between pages
  });
}

export function useOrder(id: string) {
  return useQuery({
    queryKey: orderKeys.detail(id),
    queryFn: ({ signal }) => get<Order>(`/orders/${id}`, signal),
  });
}

/** Optimistic: the UI changes instantly, rolls back on error. */
export function useCancelOrder(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => send<Order>("POST", `/orders/${id}/cancel`),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: orderKeys.detail(id) });
      const previous = qc.getQueryData<Order>(orderKeys.detail(id));
      if (previous) qc.setQueryData<Order>(orderKeys.detail(id), { ...previous, status: "cancelled" });
      return { previous };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous) qc.setQueryData(orderKeys.detail(id), ctx.previous);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: orderKeys.all }),
  });
}
