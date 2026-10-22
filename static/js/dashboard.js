const attendanceList = document.getElementById("attendance-list");
const listMessage = document.getElementById("list-message");
const modal = document.getElementById("attendance-modal");
const attendanceForm = document.getElementById("attendance-form");
const formMessage = document.getElementById("form-message");
const modalTitle = document.getElementById("modal-title");
const saveButton = document.getElementById("save-button");

let attendanceRecords = [];
let editingId = null;

function getLocalDate() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");

    return `${year}-${month}-${day}`;
}

async function loadAttendance() {
    listMessage.textContent = "";

    try {
        const response = await fetch("/api/attendance");
        const result = await response.json();

        if (!response.ok) {
            listMessage.textContent = result.error;
            return;
        }

        attendanceRecords = result.attendance;
        renderAttendance();
    } catch (error) {
        listMessage.textContent = "勤怠一覧の取得中に通信エラーが発生しました。";
    }
}

function renderAttendance() {
    attendanceList.replaceChildren();

    if (attendanceRecords.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 7;
        cell.textContent = "勤怠記録がありません。";

        row.appendChild(cell);
        attendanceList.appendChild(row);
        return;
    }

    attendanceRecords.forEach((record) => {
        const row = document.createElement("tr");

        const values = [
            record.work_date,
            record.clock_in,
            record.clock_out,
            record.break_start || "-",
            record.break_end || "-",
            record.memo || "-"
        ];

        values.forEach((value) => {
            const cell = document.createElement("td");
            cell.textContent = value;
            row.appendChild(cell);
        });

        const actionCell = document.createElement("td");

        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.textContent = "編集";
        editButton.addEventListener("click", () => openEditModal(record));

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.textContent = "削除";
        deleteButton.className = "delete-button";
        deleteButton.addEventListener("click", () => deleteAttendance(record));

        actionCell.appendChild(editButton);
        actionCell.appendChild(deleteButton);
        row.appendChild(actionCell);

        attendanceList.appendChild(row);
    });
}

async function openAddModal() {
    editingId = null;
    attendanceForm.reset();
    formMessage.textContent = "";
    modalTitle.textContent = "勤怠登録";

    document.getElementById("work-date").value = getLocalDate();

    try {
        const response = await fetch("/api/attendance/settings");
        const settings = await response.json();

        if (!response.ok) {
            formMessage.textContent = settings.error;
            return;
        }

        document.getElementById("clock-in").value = settings.clock_in;
        document.getElementById("clock-out").value = settings.clock_out;
        document.getElementById("break-start").value = settings.break_start;
        document.getElementById("break-end").value = settings.break_end;

        modal.showModal();

    } catch (error) {
        listMessage.textContent = "勤務時間設定の取得中に通信エラーが発生しました。";
    }
}

function openEditModal(record) {
    editingId = record.id;
    attendanceForm.reset();
    formMessage.textContent = "";
    modalTitle.textContent = "勤怠編集";

    document.getElementById("work-date").value = record.work_date;
    document.getElementById("clock-in").value = record.clock_in;
    document.getElementById("clock-out").value = record.clock_out;
    document.getElementById("break-start").value = record.break_start || "";
    document.getElementById("break-end").value = record.break_end || "";
    document.getElementById("memo").value = record.memo || "";

    modal.showModal();
}

attendanceForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    formMessage.textContent = "";
    saveButton.disabled = true;

    const data = {
        work_date: document.getElementById("work-date").value,
        clock_in: document.getElementById("clock-in").value,
        clock_out: document.getElementById("clock-out").value,
        break_start: document.getElementById("break-start").value || null,
        break_end: document.getElementById("break-end").value || null,
        memo: document.getElementById("memo").value
    };

    const url = editingId === null
        ? "/api/attendance"
        : `/api/attendance/${editingId}`;

    const method = editingId === null ? "POST" : "PUT";

    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (!response.ok) {
            formMessage.textContent = result.error;
            return;
        }

        modal.close();
        await loadAttendance();

    } catch (error) {
        formMessage.textContent = "保存中に通信エラーが発生しました。";

    } finally {
        saveButton.disabled = false;
    }
});

async function deleteAttendance(record) {
    const confirmed = window.confirm(
        `${record.work_date}の勤怠記録を削除しますか？`
    );

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(`/api/attendance/${record.id}`, {
            method: "DELETE"
        });

        const result = await response.json();

        if (!response.ok) {
            listMessage.textContent = result.error;
            return;
        }

        await loadAttendance();

    } catch (error) {
        listMessage.textContent = "削除中に通信エラーが発生しました。";
    }
}

document.getElementById("add-button").addEventListener(
    "click",
    openAddModal
);

document.getElementById("close-button").addEventListener(
    "click",
    () => modal.close()
);

document.getElementById("cancel-button").addEventListener(
    "click",
    () => modal.close()
);

document.getElementById("logout-button").addEventListener(
    "click",
    async () => {
        try {
            const response = await fetch("/api/logout", {
                method: "POST"
            });

            if (!response.ok) {
                listMessage.textContent = "ログアウトに失敗しました。";
                return;
            }

            window.location.href = "/login";

        } catch (error) {
            listMessage.textContent = "通信エラーが発生しました。";
        }
    }
);

loadAttendance();