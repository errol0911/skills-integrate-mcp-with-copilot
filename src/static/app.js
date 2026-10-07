document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const loginForm = document.getElementById("login-form");
  const accountPanel = document.getElementById("account-panel");
  const accountLabel = document.getElementById("account-label");
  const logoutButton = document.getElementById("logout-button");
  const messageDiv = document.getElementById("message");
  let currentAccount = null;

  function showMessage(message, type) {
    messageDiv.textContent = message;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");
  }

  async function responseMessage(response) {
    const result = await response.json();
    return result.detail || result.message || "An error occurred";
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) throw new Error("Failed to load activities");
      const activities = await response.json();
      const myActivities = currentAccount?.role === "student"
        ? await fetch("/my/activities").then(async (myResponse) => {
            if (!myResponse.ok) throw new Error("Unable to load your activities");
            return myResponse.json();
          })
        : [];
      const myActivitySet = new Set(myActivities);
      const adminActivities = currentAccount?.role === "admin"
        ? await fetch("/admin/activities").then((adminResponse) => {
            if (!adminResponse.ok) throw new Error("Unable to load admin roster");
            return adminResponse.json();
          })
        : null;

      activitiesList.replaceChildren();
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));
      Object.entries(activities).forEach(([name, details]) => {
        const card = document.createElement("article");
        card.className = "activity-card";

        const title = document.createElement("h4");
        title.textContent = name;
        card.append(title);

        const description = document.createElement("p");
        description.textContent = details.description;
        card.append(description);

        const schedule = document.createElement("p");
        schedule.textContent = `Schedule: ${details.schedule}`;
        card.append(schedule);

        const availability = document.createElement("p");
        availability.textContent = `Availability: ${Math.max(
          0,
          details.max_participants - details.participant_count
        )} spots left`;
        card.append(availability);

        if (myActivitySet.has(name)) {
          const unregisterButton = document.createElement("button");
          unregisterButton.type = "button";
          unregisterButton.textContent = "Unregister";
          unregisterButton.addEventListener("click", () => handleUnregister(name));
          card.append(unregisterButton);
        }

        if (adminActivities) {
          const heading = document.createElement("h5");
          heading.textContent = "Participant roster";
          card.append(heading);
          const roster = document.createElement("ul");
          adminActivities[name].participants.forEach((email) => {
            const participant = document.createElement("li");
            participant.textContent = email;
            roster.append(participant);
          });
          if (roster.childElementCount === 0) {
            const empty = document.createElement("li");
            empty.textContent = "No participants yet";
            roster.append(empty);
          }
          card.append(roster);
        }

        activitiesList.append(card);
        activitySelect.add(new Option(name, name));
      });
    } catch (error) {
      activitiesList.textContent = "Failed to load activities. Please try again later.";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(activity) {
    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/unregister`,
        { method: "DELETE" }
      );
      if (!response.ok) throw new Error(await responseMessage(response));
      showMessage(await responseMessage(response), "success");
      await fetchActivities();
    } catch (error) {
      showMessage(error.message || "Unable to unregister.", "error");
    }
  }

  async function refreshAccount() {
    try {
      const response = await fetch("/auth/me");
      currentAccount = response.ok ? await response.json() : null;
    } catch (error) {
      currentAccount = null;
    }

    loginForm.classList.toggle("hidden", Boolean(currentAccount));
    accountPanel.classList.toggle("hidden", !currentAccount);
    signupForm.classList.toggle("hidden", currentAccount?.role !== "student");
    if (currentAccount) {
      accountLabel.textContent = `Signed in as ${currentAccount.email} (${currentAccount.role})`;
    }
    await fetchActivities();
  }

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: document.getElementById("login-email").value,
          password: document.getElementById("login-password").value,
        }),
      });
      if (!response.ok) throw new Error(await responseMessage(response));
      loginForm.reset();
      await refreshAccount();
      showMessage("Signed in successfully.", "success");
    } catch (error) {
      showMessage(error.message || "Unable to sign in.", "error");
    }
  });

  logoutButton.addEventListener("click", async () => {
    await fetch("/auth/logout", { method: "POST" });
    currentAccount = null;
    await refreshAccount();
    showMessage("Signed out.", "success");
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const activity = activitySelect.value;
    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup`,
        { method: "POST" }
      );
      if (!response.ok) throw new Error(await responseMessage(response));
      showMessage(await responseMessage(response), "success");
      await fetchActivities();
    } catch (error) {
      showMessage(error.message || "Unable to sign up.", "error");
    }
  });

  refreshAccount();
});