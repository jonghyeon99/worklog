
const grantList = document.getElementById("grant-list");
const usageList = document.getElementById("usage-list");
const pageMessage = document.getElementById("page-message");

const totalGranted = document.getElementById("total-granted");
const totalUsed = document.getElementById("total-used");
const totalRemaining = document.getElementById("total-remaining");

const grantModal = document.getElementById("grant-modal");
const grantForm = document.getElementById("grant-form");
const grantModalTitle = document.getElementById("grant-modal-title");
const grantFormMessage = document.getElementById("grant-form-message");
const grantSaveButton = document.getElementById("grant-save-button");

const usageModal = document.getElementById("usage-modal");
const usageForm = document.getElementById("usage-form");
const usageModalTitle = document.getElementById("usage-modal-title");
const usageFormMessage = document.getElementById("usage-form-message");
const usageSaveButton = document.getElementById("usage-save-button");

let grantRecords = [];
let usageRecords = [];
let editingGrantId = null;
let editingUsageId = null;

function getLocalDate() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");

    return `${year}-${month}-${day}`;
}

function formatDays(days) {
    return `${Number(days).toFixed(1)}日`;
}

function formatDate(value) {
    return value ? value.replaceAll("-", "/") : "-";
}

function getLeaveTypeName(type) {
    if (type === "FULL") {
        return "全日";
    }

    if (type === "AM") {
        return "午前半休";
    }

    if (type === "PM") {
        return "午後半休";
    }

    return type;
}

async function apiRequest(url, options = {}) {
    const response = await fetch(url, options);
    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.error || "処理に失敗しました。");
    }

    return result;
}

async function loadLeaveData() {
    pageMessage.textContent = "";

    try {
        const [grantResult, usageResult] = await Promise.all([
            apiRequest("/api/leave/grants"),
            apiRequest("/api/leave/usage")
        ]);

        grantRecords = grantResult.grants;
        usageRecords = usageResult.usage;

        renderGrants();
        renderUsage();
        updateSummary();

    } catch (error) {
        pageMessage.textContent =
            error.message || "有給休暇情報の取得に失敗しました。";
    }
}

function updateSummary() {
    const granted = grantRecords.reduce(
        (sum, record) => sum + Number(record.granted_days),
        0
    );

    const used = grantRecords.reduce(
        (sum, record) => sum + Number(record.used_days),
        0
    );

    const remaining = grantRecords.reduce(
        (sum, record) => sum + Number(record.remaining_days),
        0
    );

    totalGranted.textContent = formatDays(granted);
    totalUsed.textContent = formatDays(used);
    totalRemaining.textContent = formatDays(remaining);
}

function createCell(value) {
    const cell = document.createElement("td");
    cell.textContent = value;
    return cell;
}

function createActionButton(text, className, callback) {
    const button = document.createElement("button");

    button.type = "button";
    button.textContent = text;
    button.className = className;
    button.addEventListener("click", callback);

    return button;
}

function renderGrants() {
    grantList.replaceChildren();

    if (grantRecords.length === 0) {
        const row = document.createElement("tr");
        const cell = createCell("有給休暇の付与履歴がありません。");

        cell.colSpan = 6;
        cell.className = "empty-message";

        row.appendChild(cell);
        grantList.appendChild(row);
        return;
    }

    grantRecords.forEach((record) => {
        const row = document.createElement("tr");

        const values = [
            formatDate(record.granted_date),
            formatDays(record.granted_days),
            formatDays(record.used_days),
            formatDays(record.remaining_days),
            formatDate(record.expires_date)
        ];

        values.forEach((value) => {
            row.appendChild(createCell(value));
        });

        const actionCell = document.createElement("td");
        actionCell.className = "action-cell";

        const editButton = createActionButton(
            "編集",
            "edit-button",
            () => openEditGrantModal(record)
        );

        const deleteButton = createActionButton(
            "削除",
            "delete-button",
            () => deleteGrant(record)
        );

        actionCell.appendChild(editButton);
        actionCell.appendChild(deleteButton);

        row.appendChild(actionCell);
        grantList.appendChild(row);
    });
}

function renderUsage() {
    usageList.replaceChildren();

    if (usageRecords.length === 0) {
        const row = document.createElement("tr");
        const cell = createCell("有給休暇の使用履歴がありません。");

        cell.colSpan = 6;
        cell.className = "empty-message";

        row.appendChild(cell);
        usageList.appendChild(row);
        return;
    }

    usageRecords.forEach((record) => {
        const row = document.createElement("tr");

        const values = [
            formatDate(record.leave_date),
            getLeaveTypeName(record.leave_type),
            formatDays(record.used_days),
            formatDate(record.granted_date),
            record.memo || "-"
        ];

        values.forEach((value) => {
            row.appendChild(createCell(value));
        });

        const actionCell = document.createElement("td");
        actionCell.className = "action-cell";

        const editButton = createActionButton(
            "編集",
            "edit-button",
            () => openEditUsageModal(record)
        );

        const deleteButton = createActionButton(
            "削除",
            "delete-button",
            () => deleteUsage(record)
        );

        actionCell.appendChild(editButton);
        actionCell.appendChild(deleteButton);

        row.appendChild(actionCell);
        usageList.appendChild(row);
    });
}

function openAddGrantModal() {
    editingGrantId = null;
    grantForm.reset();
    grantFormMessage.textContent = "";
    grantModalTitle.textContent = "有給休暇付与登録";

    document.getElementById("granted-date").value = getLocalDate();

    grantModal.showModal();
}

function openEditGrantModal(record) {
    editingGrantId = record.id;
    grantForm.reset();
    grantFormMessage.textContent = "";
    grantModalTitle.textContent = "有給休暇付与編集";

    document.getElementById("granted-date").value = record.granted_date;
    document.getElementById("granted-days").value = record.granted_days;
    document.getElementById("expires-date").value = record.expires_date;

    grantModal.showModal();
}

grantForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    grantFormMessage.textContent = "";
    grantSaveButton.disabled = true;

    const data = {
        granted_date: document.getElementById("granted-date").value,
        granted_days: Number(
            document.getElementById("granted-days").value
        ),
        expires_date: document.getElementById("expires-date").value
    };

    const url = editingGrantId === null
        ? "/api/leave/grants"
        : `/api/leave/grants/${editingGrantId}`;

    const method = editingGrantId === null ? "POST" : "PUT";

    try {
        await apiRequest(url, {
            method: method,
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        grantModal.close();
        await loadLeaveData();

    } catch (error) {
        grantFormMessage.textContent =
            error.message || "保存に失敗しました。";

    } finally {
        grantSaveButton.disabled = false;
    }
});

async function deleteGrant(record) {
    const confirmed = window.confirm(
        `${record.granted_date}の有給休暇付与履歴を削除しますか？`
    );

    if (!confirmed) {
        return;
    }

    pageMessage.textContent = "";

    try {
        await apiRequest(`/api/leave/grants/${record.id}`, {
            method: "DELETE"
        });

        await loadLeaveData();

    } catch (error) {
        pageMessage.textContent =
            error.message || "削除に失敗しました。";
    }
}

function openAddUsageModal() {
    editingUsageId = null;
    usageForm.reset();
    usageFormMessage.textContent = "";
    usageModalTitle.textContent = "有給休暇使用登録";

    document.getElementById("leave-date").value = getLocalDate();
    document.getElementById("leave-type").value = "FULL";

    usageModal.showModal();
}

function openEditUsageModal(record) {
    editingUsageId = record.id;
    usageForm.reset();
    usageFormMessage.textContent = "";
    usageModalTitle.textContent = "有給休暇使用編集";

    document.getElementById("leave-date").value = record.leave_date;
    document.getElementById("leave-type").value = record.leave_type;
    document.getElementById("leave-memo").value = record.memo || "";

    usageModal.showModal();
}

usageForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    usageFormMessage.textContent = "";
    usageSaveButton.disabled = true;

    const data = {
        leave_date: document.getElementById("leave-date").value,
        leave_type: document.getElementById("leave-type").value,
        memo: document.getElementById("leave-memo").value
    };

    const url = editingUsageId === null
        ? "/api/leave/usage"
        : `/api/leave/usage/${editingUsageId}`;

    const method = editingUsageId === null ? "POST" : "PUT";

    try {
        await apiRequest(url, {
            method: method,
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        usageModal.close();
        await loadLeaveData();

    } catch (error) {
        usageFormMessage.textContent =
            error.message || "保存に失敗しました。";

    } finally {
        usageSaveButton.disabled = false;
    }
});

async function deleteUsage(record) {
    const confirmed = window.confirm(
        `${record.leave_date}の有給休暇使用履歴を削除しますか？`
    );

    if (!confirmed) {
        return;
    }

    pageMessage.textContent = "";

    try {
        await apiRequest(`/api/leave/usage/${record.id}`, {
            method: "DELETE"
        });

        await loadLeaveData();

    } catch (error) {
        pageMessage.textContent =
            error.message || "削除に失敗しました。";
    }
}

document.getElementById("add-grant-button").addEventListener(
    "click",
    openAddGrantModal
);

document.getElementById("add-usage-button").addEventListener(
    "click",
    openAddUsageModal
);

document.getElementById("grant-close-button").addEventListener(
    "click",
    () => grantModal.close()
);

document.getElementById("grant-cancel-button").addEventListener(
    "click",
    () => grantModal.close()
);

document.getElementById("usage-close-button").addEventListener(
    "click",
    () => usageModal.close()
);

document.getElementById("usage-cancel-button").addEventListener(
    "click",
    () => usageModal.close()
);

document.getElementById("logout-button").addEventListener(
    "click",
    async () => {
        try {
            await apiRequest("/api/logout", {
                method: "POST"
            });

            window.location.href = "/login";

        } catch (error) {
            pageMessage.textContent =
                error.message || "ログアウトに失敗しました。";
        }
    }
);

loadLeaveData();
