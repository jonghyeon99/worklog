const attendanceList = document.getElementById("attendance-list");
const listMessage = document.getElementById("list-message");
const modal = document.getElementById("attendance-modal");
const attendanceForm = document.getElementById("attendance-form");
const formMessage = document.getElementById("form-message");
const modalTitle = document.getElementById("modal-title");
const saveButton = document.getElementById("save-button");
const targetMonth = document.getElementById("target-month");
const searchButton = document.getElementById("search-button");
const totalWorkTime = document.getElementById("total-work-time");
const workDays = document.getElementById("work-days");
const calendarGrid = document.getElementById("attendance-calendar");
const calendarMonth = document.getElementById("calendar-month");
const calendarPrev = document.getElementById("calendar-prev");
const calendarNext = document.getElementById("calendar-next");

let leaveRecords = [];
let attendanceRequestId = 0;
let attendanceRecords = [];
let editingId = null;

function getLocalDate() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");

    return `${year}-${month}-${day}`;
}

targetMonth.value = getLocalDate().slice(0, 7);

async function loadAttendance() {
    const requestId = ++attendanceRequestId;

    listMessage.textContent = "";

    if (!targetMonth.value) {
        listMessage.textContent = "対象年月を選択してください。";
        return;
    }

    const [year, month] = targetMonth.value.split("-");

    try {
        const [attendanceResponse, leaveResponse] = await Promise.all([
            fetch(`/api/attendance?year=${year}&month=${month}`),
            fetch("/api/leave/usage")
        ]);

        const [attendanceResult, leaveResult] = await Promise.all([
            attendanceResponse.json(),
            leaveResponse.json()
        ]);

        // 이전 달 요청이 늦게 도착해 화면을 덮어쓰는 문제 방지
        if (requestId !== attendanceRequestId) {
            return;
        }

        if (!attendanceResponse.ok) {
            listMessage.textContent =
                attendanceResult.error || "勤怠一覧を取得できませんでした。";
            return;
        }

        attendanceRecords = attendanceResult.attendance;
        workDays.textContent = `${attendanceResult.work_days}日`;
        totalWorkTime.textContent = attendanceResult.total_work_time;

        if (leaveResponse.ok) {
            leaveRecords = leaveResult.usage.filter(
                record => record.leave_date.startsWith(targetMonth.value + "-")
            );
        } else {
            leaveRecords = [];
            listMessage.textContent =
                "有給休暇の情報を取得できませんでした。";
        }

        renderAttendance();
        renderCalendar();

    } catch (error) {
        if (requestId === attendanceRequestId) {
            listMessage.textContent =
                "勤怠・休暇情報の取得中に通信エラーが発生しました。";
        }
    }
}

function renderAttendance() {
    attendanceList.replaceChildren();

    if (attendanceRecords.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 8;
        cell.className = "empty-message";
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
            record.work_time,
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

function renderCalendar() {
    calendarGrid.replaceChildren();

    if (!targetMonth.value) {
        calendarMonth.textContent = "";
        return;
    }

    const [year, month] = targetMonth.value.split("-").map(Number);

    calendarMonth.textContent = `${year}年${month}月`;

    const firstDay = new Date(year, month - 1, 1).getDay();
    const daysInMonth = new Date(year, month, 0).getDate();

    const attendanceMap = new Map(
        attendanceRecords.map(record => [record.work_date, record])
    );

    const leaveMap = new Map(
        leaveRecords.map(record => [record.leave_date, record])
    );

    const today = getLocalDate();

    for (let i = 0; i < firstDay; i++) {
        const empty = document.createElement("div");
        empty.className = "calendar-empty";
        calendarGrid.appendChild(empty);
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const date =
            `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;

        const attendance = attendanceMap.get(date);
        const leave = leaveMap.get(date);

        const button = document.createElement("button");
        button.type = "button";
        button.className = "calendar-day";

        if (date === today) {
            button.classList.add("today");
        }

        const dateLabel = document.createElement("span");
        dateLabel.className = "calendar-date";
        dateLabel.textContent = day;
        button.appendChild(dateLabel);

        const statuses = [];

        function addStatus(label, type) {
            const status = document.createElement("span");
            status.className = `calendar-status ${type}`;
            status.textContent = label;
            button.appendChild(status);
            statuses.push(label);
        }

        if (leave) {
            if (leave.leave_type === "FULL") {
                addStatus("有給", "leave");
            } else if (leave.leave_type === "AM") {
                addStatus("午前休", "half");
            } else if (leave.leave_type === "PM") {
                addStatus("午後休", "half");
            }
        }

        if (attendance) {
            addStatus("出勤", "work");
        }

        button.setAttribute(
            "aria-label",
            `${date} ${statuses.length ? statuses.join("、") : "未登録"}`
        );

        button.addEventListener("click", () => {
            if (attendance) {
                openEditModal(attendance);
            } else if (leave) {
                window.location.href = "/leave";
            } else {
                openAddModal(date);
            }
        });

        calendarGrid.appendChild(button);
    }
}

async function openAddModal(selectedDate = null) {
    editingId = null;
    attendanceForm.reset();
    formMessage.textContent = "";
    modalTitle.textContent = "勤怠登録";

    document.getElementById("work-date").value = typeof selectedDate === "string" ? selectedDate : getLocalDate();

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

searchButton.addEventListener("click", loadAttendance);

function changeCalendarMonth(offset) {
    if (!targetMonth.value) {
        return;
    }

    const [year, month] = targetMonth.value.split("-").map(Number);
    const newDate = new Date(year, month - 1 + offset, 1);

    targetMonth.value =
        `${newDate.getFullYear()}-${String(newDate.getMonth() + 1).padStart(2, "0")}`;

    loadAttendance();
}

calendarPrev.addEventListener("click", () => {
    changeCalendarMonth(-1);
});

calendarNext.addEventListener("click", () => {
    changeCalendarMonth(1);
});

loadAttendance();