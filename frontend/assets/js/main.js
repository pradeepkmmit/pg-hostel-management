const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000/api`;

const menuToggle = document.querySelector(".menu-toggle");
const siteNavigation = document.querySelector(".site-nav");
const roomGrid = document.querySelector(".room-grid");
const roomListingStatus = document.querySelector(".room-listing-status");
const portalAuth = document.querySelector("#portal-auth");
const portalDashboard = document.querySelector("#portal-dashboard");
const portalGlobalNotice = document.querySelector("#portal-global-notice");
let availableRooms = [];

const roomVisuals = {
  private: {
    imageClass: "room-image-private",
    imageDescription: "Illustration of a private furnished room",
  },
  shared: {
    imageClass: "room-image-shared",
    imageDescription: "Illustration of a bright shared room",
  },
  suite: {
    imageClass: "room-image-suite",
    imageDescription: "Illustration of a spacious private suite",
  },
};
const inrFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

function makeElement(tagName, className = "", text = "") {
  const element = document.createElement(tagName);
  if (className) {
    element.className = className;
  }
  if (text) {
    element.textContent = text;
  }
  return element;
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  if (response.status === 204) {
    return null;
  }
  const result = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(result.detail)
      ? result.detail.map((issue) => issue.msg).join(" ")
      : result.detail;
    throw new Error(detail || `Request failed (${response.status}).`);
  }
  return result;
}

function formValues(form, numbers = []) {
  const values = Object.fromEntries(new FormData(form));
  for (const key of numbers) {
    if (values[key] !== "") {
      values[key] = Number(values[key]);
    }
  }
  return values;
}

function showFormNotice(form, message, isError = false) {
  const notice = form.querySelector(".portal-notice");
  notice.textContent = message;
  notice.classList.toggle("is-error", isError);
}

function roomCard(room) {
  const visual = roomVisuals[room.room_type];
  if (!visual) {
    return null;
  }

  const card = makeElement("article", "room-card");
  const image = makeElement("div", `room-image ${visual.imageClass}`);
  image.setAttribute("role", "img");
  image.setAttribute("aria-label", visual.imageDescription);
  image.append(makeElement("span", "room-tag", room.tag));

  const illustration = makeElement("div", "mini-room");
  illustration.append(makeElement("span"), makeElement("i"), makeElement("b"));
  if (room.room_type === "shared") {
    illustration.append(makeElement("em"));
  }
  image.append(illustration);

  const details = makeElement("div", "room-details");
  const description = makeElement("div");
  description.append(
    makeElement("h3", "", room.name),
    makeElement("p", "", room.description),
  );
  const arrow = makeElement("span", "room-arrow", "↗");
  arrow.setAttribute("aria-hidden", "true");
  details.append(description, arrow);

  const price = makeElement("div", "room-price");
  price.append(makeElement("span", "", "Monthly rent"));
  const rent = makeElement("strong", "", inrFormatter.format(room.monthly_rent));
  rent.append(makeElement("small", "", " / month"));
  price.append(rent);
  card.append(image, details, price);

  card.addEventListener("click", () => {
    const selector = document.querySelector("#booking-room");
    if (selector && Array.from(selector.options).some((option) => Number(option.value) === room.id)) {
      selector.value = String(room.id);
      window.location.hash = "#portal";
    }
  });
  card.classList.add("room-card-bookable");
  card.setAttribute("tabindex", "0");
  card.setAttribute("aria-label", `${room.name}, ${inrFormatter.format(room.monthly_rent)} per month. Sign in to request this room.`);
  card.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      card.click();
    }
  });
  return card;
}

function renderRoomCards(rooms) {
  const cards = rooms.map(roomCard).filter(Boolean);
  roomGrid.replaceChildren(...cards);
  roomListingStatus.textContent = cards.length
    ? ""
    : "There are no rooms available right now. Please check back soon.";
  const bookingRoomSelect = document.querySelector("#booking-room");
  if (bookingRoomSelect) {
    bookingRoomSelect.replaceChildren();
    if (rooms.length === 0) {
      bookingRoomSelect.append(new Option("No rooms currently available", ""));
      bookingRoomSelect.disabled = true;
    } else {
      bookingRoomSelect.disabled = false;
      for (const room of rooms) {
        bookingRoomSelect.append(
          new Option(`${room.name} — ${inrFormatter.format(room.monthly_rent)}/month`, room.id),
        );
      }
    }
  }
}

async function loadRooms() {
  roomListingStatus.textContent = "Loading available rooms…";
  try {
    availableRooms = await api("/rooms");
    renderRoomCards(availableRooms);
  } catch {
    roomListingStatus.textContent =
      "We couldn't load room listings. Please make sure the local API is running, then refresh.";
  }
}

function renderRecordList(target, records, renderRecord, emptyMessage) {
  const container = document.querySelector(target);
  container.replaceChildren();
  if (records.length === 0) {
    container.append(makeElement("p", "portal-empty", emptyMessage));
    return;
  }
  for (const record of records) {
    container.append(renderRecord(record));
  }
}

function recordCard(title, lines, status, actions = []) {
  const card = makeElement("article", "portal-record");
  card.append(makeElement("h4", "", title));
  for (const line of lines) {
    card.append(makeElement("p", "", line));
  }
  if (status) {
    card.append(makeElement("span", `status-pill status-${status}`, status.replaceAll("_", " ")));
  }
  if (actions.length) {
    const actionRow = makeElement("div", "portal-record-actions");
    actionRow.append(...actions);
    card.append(actionRow);
  }
  return card;
}

function actionButton(label, action, id, className = "button button-small") {
  const button = makeElement("button", className, label);
  button.type = "button";
  button.dataset.action = action;
  button.dataset.id = String(id);
  return button;
}

function formatDate(value) {
  if (!value) {
    return "Not specified";
  }
  return new Date(`${value}T00:00:00`).toLocaleDateString();
}

function showPortal(user) {
  portalAuth.hidden = true;
  portalDashboard.hidden = false;
  document.querySelector("#portal-welcome").textContent = `Hello, ${user.name}`;
  document.querySelector("#portal-identity").textContent = `${user.email} · ${user.role}`;
  const isAdmin = user.role === "admin";
  document.querySelector("#resident-dashboard").hidden = isAdmin;
  document.querySelector("#admin-dashboard").hidden = !isAdmin;
  portalGlobalNotice.textContent = "";
  if (isAdmin) {
    loadAdminDashboard();
  } else {
    loadResidentDashboard();
  }
}

function showSignedOut() {
  portalAuth.hidden = false;
  portalDashboard.hidden = true;
  document.querySelector("#resident-dashboard").hidden = true;
  document.querySelector("#admin-dashboard").hidden = true;
}

async function loadResidentDashboard() {
  try {
    const [profile, bookings, maintenance, payments, notices] = await Promise.all([
      api("/resident/profile"),
      api("/resident/bookings"),
      api("/resident/maintenance"),
      api("/resident/payments"),
      api("/resident/notices"),
    ]);
    document.querySelector("#profile-name").value = profile.name;
    document.querySelector("#profile-phone").value = profile.phone;
    renderRecordList(
      "#resident-bookings",
      bookings,
      (booking) =>
        recordCard(booking.room_name, [
          `Move-in: ${formatDate(booking.move_in_date)}`,
          booking.message || "No note provided.",
        ], booking.status),
      "You haven't requested a room yet.",
    );
    renderRecordList(
      "#resident-maintenance",
      maintenance,
      (request) =>
        recordCard(request.category, [request.description, formatDate(request.created_at.slice(0, 10))], request.status),
      "No maintenance requests.",
    );
    renderRecordList(
      "#resident-payments",
      payments,
      (payment) =>
        recordCard(`${payment.billing_period} · ${inrFormatter.format(payment.amount)}`, [
          `Due ${formatDate(payment.due_date)}`,
          payment.note || "Rent record",
        ], payment.status),
      "No rent records yet.",
    );
    renderRecordList(
      "#resident-notices",
      notices,
      (notice) => recordCard(notice.title, [notice.message, `Posted by ${notice.author_name}`], ""),
      "No notices have been posted.",
    );
  } catch (error) {
    portalGlobalNotice.textContent = error.message;
  }
}

async function loadAdminDashboard() {
  try {
    const [rooms, bookings, maintenance, residents, notices, inquiries, payments] =
      await Promise.all([
        api("/admin/rooms"),
        api("/admin/bookings"),
        api("/admin/maintenance"),
        api("/admin/residents"),
        api("/admin/notices"),
        api("/admin/inquiries"),
        api("/admin/payments"),
      ]);
    renderRecordList(
      "#admin-rooms",
      rooms,
      (room) =>
        recordCard(`${room.name} · ${inrFormatter.format(room.monthly_rent)}/month`, [
          room.description,
          room.available ? "Listed as available" : "Currently unavailable",
        ], room.available ? "available" : "unavailable", [
          actionButton(room.available ? "Mark unavailable" : "List as available", "room-availability", room.id),
        ]),
      "No room listings.",
    );
    renderRecordList(
      "#admin-bookings",
      bookings,
      (booking) =>
        recordCard(`${booking.room_name} · ${booking.resident_name}`, [
          booking.resident_email,
          `Move-in: ${formatDate(booking.move_in_date)}`,
          booking.message || "No note provided.",
        ], booking.status, booking.status === "pending" ? [
          actionButton("Approve", "approve-booking", booking.id, "button button-small"),
          actionButton("Decline", "reject-booking", booking.id, "button button-small button-danger"),
        ] : []),
      "No booking requests.",
    );
    renderRecordList(
      "#admin-maintenance",
      maintenance,
      (request) =>
        recordCard(`${request.category} · ${request.resident_name}`, [
          request.description,
          formatDate(request.created_at.slice(0, 10)),
        ], request.status, request.status !== "resolved" ? [
          actionButton("Mark resolved", "resolve-maintenance", request.id),
        ] : []),
      "No maintenance requests.",
    );
    renderRecordList(
      "#admin-payments",
      payments,
      (payment) =>
        recordCard(`${payment.resident_name} · ${inrFormatter.format(payment.amount)}`, [
          payment.billing_period,
          `Due ${formatDate(payment.due_date)}`,
        ], payment.status, [
          actionButton(
            payment.status === "paid" ? "Mark due" : "Mark paid",
            "toggle-payment",
            payment.id,
          ),
        ]),
      "No rent records.",
    );
    renderRecordList(
      "#admin-residents",
      residents,
      (resident) => recordCard(resident.name, [resident.email, resident.phone || "No phone provided"], ""),
      "No resident accounts.",
    );
    renderRecordList(
      "#admin-notices",
      notices,
      (notice) => recordCard(notice.title, [notice.message], "", [
        actionButton("Delete", "delete-notice", notice.id, "button button-small button-danger"),
      ]),
      "No notices have been published.",
    );
    renderRecordList(
      "#admin-inquiries",
      inquiries,
      (inquiry) =>
        recordCard(inquiry.name, [inquiry.email, inquiry.message || "No message provided.", inquiry.created_at], ""),
      "No visitor inquiries.",
    );
    const residentSelect = document.querySelector("#payment-resident");
    residentSelect.replaceChildren();
    if (residents.length === 0) {
      residentSelect.append(new Option("No resident accounts", ""));
      residentSelect.disabled = true;
    } else {
      residentSelect.disabled = false;
      for (const resident of residents) {
        residentSelect.append(new Option(`${resident.name} (${resident.email})`, resident.id));
      }
    }
  } catch (error) {
    portalGlobalNotice.textContent = error.message;
  }
}

menuToggle.addEventListener("click", () => {
  const isExpanded = menuToggle.getAttribute("aria-expanded") === "true";
  menuToggle.setAttribute("aria-expanded", String(!isExpanded));
  menuToggle.setAttribute(
    "aria-label",
    isExpanded ? "Open navigation menu" : "Close navigation menu",
  );
  siteNavigation.classList.toggle("is-open", !isExpanded);
});

siteNavigation.addEventListener("click", (event) => {
  if (event.target.closest("a")) {
    menuToggle.setAttribute("aria-expanded", "false");
    menuToggle.setAttribute("aria-label", "Open navigation menu");
    siteNavigation.classList.remove("is-open");
  }
});

document.querySelector(".contact-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const notice = form.querySelector(".form-notice");
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  notice.textContent = "";
  try {
    const result = await api("/inquiries", {
      method: "POST",
      body: JSON.stringify(formValues(form)),
    });
    notice.textContent = result.message;
    form.reset();
  } catch (error) {
    notice.textContent = error instanceof TypeError
      ? "We couldn't connect to the local API. Please check that the backend is running and try again."
      : error.message;
  } finally {
    button.disabled = false;
  }
});

document.querySelector("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const user = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify(formValues(form)),
    });
    form.reset();
    showPortal(user);
  } catch (error) {
    showFormNotice(form, error.message, true);
  }
});

document.querySelector("#register-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const user = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify(formValues(form)),
    });
    form.reset();
    showPortal(user);
  } catch (error) {
    showFormNotice(form, error.message, true);
  }
});

document.querySelector("#logout-button").addEventListener("click", async () => {
  try {
    await api("/auth/logout", { method: "POST" });
    showSignedOut();
  } catch (error) {
    portalGlobalNotice.textContent = error.message;
  }
});

document.querySelector("#booking-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    await api("/resident/bookings", {
      method: "POST",
      body: JSON.stringify(formValues(form, ["room_id"])),
    });
    form.reset();
    showFormNotice(form, "Your booking request was sent to the team.");
    await loadResidentDashboard();
  } catch (error) {
    showFormNotice(form, error.message, true);
  }
});

document.querySelector("#profile-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const profile = await api("/resident/profile", {
      method: "PATCH",
      body: JSON.stringify(formValues(form)),
    });
    document.querySelector("#portal-welcome").textContent = `Hello, ${profile.name}`;
    showFormNotice(form, "Your profile was updated.");
  } catch (error) {
    showFormNotice(form, error.message, true);
  }
});

document.querySelector("#maintenance-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    await api("/resident/maintenance", {
      method: "POST",
      body: JSON.stringify(formValues(form)),
    });
    form.reset();
    showFormNotice(form, "Your maintenance request was submitted.");
    await loadResidentDashboard();
  } catch (error) {
    showFormNotice(form, error.message, true);
  }
});

document.querySelector("#room-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    await api("/admin/rooms", {
      method: "POST",
      body: JSON.stringify(formValues(form, ["monthly_rent"])),
    });
    form.reset();
    showFormNotice(form, "Room listing added.");
    await loadAdminDashboard();
    await loadRooms();
  } catch (error) {
    showFormNotice(form, error.message, true);
  }
});

document.querySelector("#payment-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    await api("/admin/payments", {
      method: "POST",
      body: JSON.stringify(formValues(form, ["user_id", "amount"])),
    });
    form.reset();
    showFormNotice(form, "Rent record saved.");
    await loadAdminDashboard();
  } catch (error) {
    showFormNotice(form, error.message, true);
  }
});

document.querySelector("#notice-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    await api("/admin/notices", {
      method: "POST",
      body: JSON.stringify(formValues(form)),
    });
    form.reset();
    showFormNotice(form, "Notice published.");
    await loadAdminDashboard();
  } catch (error) {
    showFormNotice(form, error.message, true);
  }
});

document.querySelector("#admin-dashboard").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) {
    return;
  }
  const { action, id } = button.dataset;
  try {
    if (action === "room-availability") {
      const room = (await api("/admin/rooms")).find((item) => item.id === Number(id));
      await api(`/admin/rooms/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ available: !room.available }),
      });
      await loadAdminDashboard();
      await loadRooms();
    } else if (action === "approve-booking" || action === "reject-booking") {
      await api(`/admin/bookings/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: action === "approve-booking" ? "approved" : "rejected" }),
      });
      await loadAdminDashboard();
      await loadRooms();
    } else if (action === "resolve-maintenance") {
      await api(`/admin/maintenance/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "resolved" }),
      });
      await loadAdminDashboard();
    } else if (action === "toggle-payment") {
      const payment = (await api("/admin/payments")).find((item) => item.id === Number(id));
      await api(`/admin/payments/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: payment.status === "paid" ? "due" : "paid" }),
      });
      await loadAdminDashboard();
    } else if (action === "delete-notice") {
      await api(`/admin/notices/${id}`, { method: "DELETE" });
      await loadAdminDashboard();
    }
  } catch (error) {
    portalGlobalNotice.textContent = error.message;
  }
});

document.querySelector("#move-in-date").min = new Date().toISOString().slice(0, 10);
loadRooms();
api("/auth/me")
  .then(showPortal)
  .catch(showSignedOut);
