(globalThis["TURBOPACK"] || (globalThis["TURBOPACK"] = [])).push([typeof document === "object" ? document.currentScript : undefined,
"[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>TimetableGrid
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
'use client';
;
function TimetableGrid({ assignments, days, view }) {
    if (!assignments.length) {
        return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            className: "flex items-center justify-center h-32 text-sm text-gray-400 dark:text-gray-500",
            children: "Aucune donnée à afficher"
        }, void 0, false, {
            fileName: "[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx",
            lineNumber: 13,
            columnNumber: 7
        }, this);
    }
    // Unique time slots sorted chronologically
    const timeSlots = [
        ...new Set(assignments.map((a)=>a.start_time))
    ].sort();
    // Fast lookup: "day||time" → assignment
    const lookup = new Map();
    for (const a of assignments){
        lookup.set(`${a.day}||${a.start_time}`, a);
    }
    function getCell(day, time) {
        return lookup.get(`${day}||${time}`);
    }
    // True when this (day, slotIndex) continues the previous slot's session
    function isContinuation(day, slotIndex) {
        if (slotIndex === 0) return false;
        const prev = getCell(day, timeSlots[slotIndex - 1]);
        const curr = getCell(day, timeSlots[slotIndex]);
        if (!prev || !curr) return false;
        return prev.teacher === curr.teacher && prev.subject === curr.subject && prev.school_class === curr.school_class;
    }
    // Secondary info line changes depending on perspective
    function subLine(a) {
        if (view === 'class') return `${a.teacher} · ${a.room}`;
        if (view === 'teacher') return `${a.school_class} · ${a.room}`;
        return `${a.school_class} · ${a.teacher}`;
    }
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "overflow-x-auto",
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("table", {
            className: "w-full border-collapse",
            children: [
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("thead", {
                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("tr", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("th", {
                                className: "w-14 border-b border-gray-200 dark:border-gray-700"
                            }, void 0, false, {
                                fileName: "[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx",
                                lineNumber: 58,
                                columnNumber: 13
                            }, this),
                            days.map((d)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("th", {
                                    className: "px-3 py-2.5 text-center text-xs font-semibold text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700 capitalize min-w-[130px]",
                                    children: d
                                }, d, false, {
                                    fileName: "[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx",
                                    lineNumber: 60,
                                    columnNumber: 15
                                }, this))
                        ]
                    }, void 0, true, {
                        fileName: "[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx",
                        lineNumber: 56,
                        columnNumber: 11
                    }, this)
                }, void 0, false, {
                    fileName: "[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx",
                    lineNumber: 55,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("tbody", {
                    children: timeSlots.map((time, ti)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("tr", {
                            className: "border-b border-gray-100 dark:border-gray-800 last:border-0",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("td", {
                                    className: "pr-2 pl-1 py-1.5 text-right text-[11px] font-mono text-gray-400 dark:text-gray-500 whitespace-nowrap align-top pt-2.5",
                                    children: time
                                }, void 0, false, {
                                    fileName: "[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx",
                                    lineNumber: 73,
                                    columnNumber: 15
                                }, this),
                                days.map((day)=>{
                                    const a = getCell(day, time);
                                    const cont = isContinuation(day, ti);
                                    if (!a) {
                                        return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("td", {
                                            className: "px-1.5 py-1.5 align-top",
                                            children: view === 'teacher' ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                className: "rounded-md p-1.5 text-xs bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 text-center h-10 flex items-center justify-center",
                                                children: "Libre"
                                            }, void 0, false, {
                                                fileName: "[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx",
                                                lineNumber: 85,
                                                columnNumber: 25
                                            }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                className: "h-10 rounded-md bg-gray-50 dark:bg-gray-800/50"
                                            }, void 0, false, {
                                                fileName: "[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx",
                                                lineNumber: 89,
                                                columnNumber: 25
                                            }, this)
                                        }, day, false, {
                                            fileName: "[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx",
                                            lineNumber: 83,
                                            columnNumber: 21
                                        }, this);
                                    }
                                    // Hex color → 20% opacity background
                                    const bg = a.color + '33';
                                    const border = a.color;
                                    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("td", {
                                        className: "px-1.5 py-1.5 align-top",
                                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                            className: "rounded-md p-1.5 text-xs leading-tight",
                                            style: {
                                                backgroundColor: bg,
                                                borderLeft: `3px solid ${border}`,
                                                borderTop: cont ? `2px dashed ${border}` : undefined
                                            },
                                            children: [
                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                                    className: "font-medium text-gray-900 dark:text-gray-100 truncate",
                                                    children: a.subject
                                                }, void 0, false, {
                                                    fileName: "[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx",
                                                    lineNumber: 109,
                                                    columnNumber: 23
                                                }, this),
                                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                                    className: "text-[11px] text-gray-500 dark:text-gray-400 truncate mt-0.5",
                                                    children: subLine(a)
                                                }, void 0, false, {
                                                    fileName: "[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx",
                                                    lineNumber: 112,
                                                    columnNumber: 23
                                                }, this)
                                            ]
                                        }, void 0, true, {
                                            fileName: "[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx",
                                            lineNumber: 101,
                                            columnNumber: 21
                                        }, this)
                                    }, day, false, {
                                        fileName: "[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx",
                                        lineNumber: 100,
                                        columnNumber: 19
                                    }, this);
                                })
                            ]
                        }, time, true, {
                            fileName: "[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx",
                            lineNumber: 71,
                            columnNumber: 13
                        }, this))
                }, void 0, false, {
                    fileName: "[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx",
                    lineNumber: 69,
                    columnNumber: 9
                }, this)
            ]
        }, void 0, true, {
            fileName: "[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx",
            lineNumber: 54,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx",
        lineNumber: 53,
        columnNumber: 5
    }, this);
}
_c = TimetableGrid;
var _c;
__turbopack_context__.k.register(_c, "TimetableGrid");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/Desktop/TIMEASE/frontend/lib/api.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "createSession",
    ()=>createSession,
    "exportFile",
    ()=>exportFile,
    "getSession",
    ()=>getSession,
    "mergeData",
    ()=>mergeData,
    "sendChat",
    ()=>sendChat,
    "solve",
    ()=>solve,
    "uploadFile",
    ()=>uploadFile
]);
const BASE = 'http://localhost:8000';
async function createSession() {
    const res = await fetch(`${BASE}/api/session`, {
        method: 'POST'
    });
    const data = await res.json();
    return data.session_id;
}
async function getSession(sid) {
    const res = await fetch(`${BASE}/api/session/${sid}`);
    return res.json();
}
async function sendChat(sid, message, fileContent) {
    const res = await fetch(`${BASE}/api/session/${sid}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message,
            file_content: fileContent
        })
    });
    return res.json();
}
async function uploadFile(sid, file) {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${BASE}/api/session/${sid}/upload`, {
        method: 'POST',
        body: form
    });
    return res.json();
}
async function mergeData(sid, type, data) {
    const res = await fetch(`${BASE}/api/session/${sid}/merge`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            type,
            data
        })
    });
    return res.json();
}
async function solve(sid) {
    const res = await fetch(`${BASE}/api/session/${sid}/solve`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            timeout: 120
        })
    });
    return res.json();
}
async function exportFile(sid, format) {
    const res = await fetch(`${BASE}/api/session/${sid}/export/${format}`);
    return res.blob();
}
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/Desktop/TIMEASE/frontend/hooks/useSession.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "useSession",
    ()=>useSession
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/lib/api.ts [app-client] (ecmascript)");
var _s = __turbopack_context__.k.signature();
'use client';
;
;
function useSession() {
    _s();
    const [sessionId, setSessionId] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [schoolData, setSchoolData] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])({});
    const [assignments, setAssignments] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])([]);
    const [timetable, setTimetable] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "useSession.useEffect": ()=>{
            const stored = localStorage.getItem('timease_session');
            if (stored) {
                setSessionId(stored);
                (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["getSession"])(stored).then({
                    "useSession.useEffect": (data)=>{
                        setSchoolData(data.school_data || {});
                        setAssignments(data.teacher_assignments || []);
                        setTimetable(data.timetable_result || null);
                    }
                }["useSession.useEffect"]).catch({
                    "useSession.useEffect": ()=>initSession()
                }["useSession.useEffect"]);
            } else {
                initSession();
            }
        }
    }["useSession.useEffect"], []);
    async function initSession() {
        const sid = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["createSession"])();
        localStorage.setItem('timease_session', sid);
        setSessionId(sid);
    }
    function refreshSession() {
        if (!sessionId) return;
        (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["getSession"])(sessionId).then((data)=>{
            setSchoolData(data.school_data || {});
            setAssignments(data.teacher_assignments || []);
            setTimetable(data.timetable_result || null);
        });
    }
    return {
        sessionId,
        schoolData,
        assignments,
        timetable,
        refreshSession
    };
}
_s(useSession, "xKoXM5Hu5hMgwAPA5bFRrcgUiek=");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/Desktop/TIMEASE/frontend/app/results/page.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>ResultsPage
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/node_modules/next/dist/client/app-dir/link.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$file$2d$down$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__FileDown$3e$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/node_modules/lucide-react/dist/esm/icons/file-down.js [app-client] (ecmascript) <export default as FileDown>");
var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$calendar$2d$days$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__CalendarDays$3e$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/node_modules/lucide-react/dist/esm/icons/calendar-days.js [app-client] (ecmascript) <export default as CalendarDays>");
var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$loader$2d$circle$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Loader2$3e$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/node_modules/lucide-react/dist/esm/icons/loader-circle.js [app-client] (ecmascript) <export default as Loader2>");
var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$components$2f$TimetableGrid$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/components/TimetableGrid.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$hooks$2f$useSession$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/hooks/useSession.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$components$2f$Toast$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/components/Toast.tsx [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/lib/api.ts [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
'use client';
;
;
;
;
;
;
;
const TABS = [
    {
        id: 'class',
        label: 'Par classe'
    },
    {
        id: 'teacher',
        label: 'Par enseignant'
    },
    {
        id: 'room',
        label: 'Par salle'
    },
    {
        id: 'subject',
        label: 'Par matière'
    }
];
const EXPORT_FORMATS = [
    {
        id: 'xlsx',
        label: 'Excel'
    },
    {
        id: 'pdf',
        label: 'PDF'
    },
    {
        id: 'docx',
        label: 'Word'
    },
    {
        id: 'md',
        label: 'Markdown'
    }
];
// ── Skeleton ──────────────────────────────────────────────────────────────────
function GridSkeleton() {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "animate-pulse space-y-2 p-4",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "h-8 bg-gray-100 dark:bg-gray-800 rounded"
            }, void 0, false, {
                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                lineNumber: 31,
                columnNumber: 7
            }, this),
            [
                ...Array(6)
            ].map((_, i)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "h-12 bg-gray-50 dark:bg-gray-800/60 rounded"
                }, i, false, {
                    fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                    lineNumber: 33,
                    columnNumber: 9
                }, this))
        ]
    }, void 0, true, {
        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
        lineNumber: 30,
        columnNumber: 5
    }, this);
}
_c = GridSkeleton;
function ResultsPage() {
    _s();
    const { sessionId, timetable } = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$hooks$2f$useSession$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useSession"])();
    const { toast } = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$components$2f$Toast$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useToast"])();
    const [activeTab, setActiveTab] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])('class');
    const [selected, setSelected] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])('');
    const [downloading, setDownloading] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const assignments = timetable?.assignments ?? [];
    const isLoading = !sessionId;
    // ── Derived entity lists ───────────────────────────────────────────────────
    const classes = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMemo"])({
        "ResultsPage.useMemo[classes]": ()=>[
                ...new Set(assignments.map({
                    "ResultsPage.useMemo[classes]": (a)=>a.school_class
                }["ResultsPage.useMemo[classes]"]))
            ].sort()
    }["ResultsPage.useMemo[classes]"], [
        assignments
    ]);
    const teachers = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMemo"])({
        "ResultsPage.useMemo[teachers]": ()=>[
                ...new Set(assignments.map({
                    "ResultsPage.useMemo[teachers]": (a)=>a.teacher
                }["ResultsPage.useMemo[teachers]"]))
            ].sort()
    }["ResultsPage.useMemo[teachers]"], [
        assignments
    ]);
    const rooms = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMemo"])({
        "ResultsPage.useMemo[rooms]": ()=>[
                ...new Set(assignments.map({
                    "ResultsPage.useMemo[rooms]": (a)=>a.room
                }["ResultsPage.useMemo[rooms]"]))
            ].sort()
    }["ResultsPage.useMemo[rooms]"], [
        assignments
    ]);
    const subjects = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMemo"])({
        "ResultsPage.useMemo[subjects]": ()=>[
                ...new Set(assignments.map({
                    "ResultsPage.useMemo[subjects]": (a)=>a.subject
                }["ResultsPage.useMemo[subjects]"]))
            ].sort()
    }["ResultsPage.useMemo[subjects]"], [
        assignments
    ]);
    const days = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMemo"])({
        "ResultsPage.useMemo[days]": ()=>{
            if (timetable?.days?.length) return timetable.days;
            return [
                ...new Set(assignments.map({
                    "ResultsPage.useMemo[days]": (a)=>a.day
                }["ResultsPage.useMemo[days]"]))
            ];
        }
    }["ResultsPage.useMemo[days]"], [
        assignments,
        timetable
    ]);
    const options = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMemo"])({
        "ResultsPage.useMemo[options]": ()=>{
            if (activeTab === 'class') return classes;
            if (activeTab === 'teacher') return teachers;
            if (activeTab === 'room') return rooms;
            return subjects;
        }
    }["ResultsPage.useMemo[options]"], [
        activeTab,
        classes,
        teachers,
        rooms,
        subjects
    ]);
    const resolvedSelected = options.includes(selected) ? selected : options[0] ?? '';
    const filtered = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMemo"])({
        "ResultsPage.useMemo[filtered]": ()=>{
            if (!resolvedSelected || activeTab === 'subject') return [];
            if (activeTab === 'class') return assignments.filter({
                "ResultsPage.useMemo[filtered]": (a)=>a.school_class === resolvedSelected
            }["ResultsPage.useMemo[filtered]"]);
            if (activeTab === 'teacher') return assignments.filter({
                "ResultsPage.useMemo[filtered]": (a)=>a.teacher === resolvedSelected
            }["ResultsPage.useMemo[filtered]"]);
            return assignments.filter({
                "ResultsPage.useMemo[filtered]": (a)=>a.room === resolvedSelected
            }["ResultsPage.useMemo[filtered]"]);
        }
    }["ResultsPage.useMemo[filtered]"], [
        assignments,
        activeTab,
        resolvedSelected
    ]);
    const subjectSummary = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMemo"])({
        "ResultsPage.useMemo[subjectSummary]": ()=>subjects.map({
                "ResultsPage.useMemo[subjectSummary]": (s)=>{
                    const rows = assignments.filter({
                        "ResultsPage.useMemo[subjectSummary].rows": (a)=>a.subject === s
                    }["ResultsPage.useMemo[subjectSummary].rows"]);
                    return {
                        subject: s,
                        sessions: rows.length,
                        teachers: [
                            ...new Set(rows.map({
                                "ResultsPage.useMemo[subjectSummary]": (a)=>a.teacher
                            }["ResultsPage.useMemo[subjectSummary]"]))
                        ].sort(),
                        classes: [
                            ...new Set(rows.map({
                                "ResultsPage.useMemo[subjectSummary]": (a)=>a.school_class
                            }["ResultsPage.useMemo[subjectSummary]"]))
                        ].sort()
                    };
                }
            }["ResultsPage.useMemo[subjectSummary]"])
    }["ResultsPage.useMemo[subjectSummary]"], [
        assignments,
        subjects
    ]);
    const softResults = timetable?.soft_results ?? [];
    // ── Export ─────────────────────────────────────────────────────────────────
    async function handleExport(format) {
        if (!sessionId || downloading) return;
        setDownloading(format);
        try {
            const blob = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$lib$2f$api$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["exportFile"])(sessionId, format);
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `emploi_du_temps.${format}`;
            a.click();
            URL.revokeObjectURL(url);
            toast('Fichier exporté');
        } catch  {
            toast('Erreur lors de l\'export', 'error');
        } finally{
            setDownloading(null);
        }
    }
    // ── Empty state (session loaded but no timetable yet) ──────────────────────
    if (!isLoading && !assignments.length) {
        return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            className: "flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center px-4",
            children: [
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "w-16 h-16 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center",
                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$calendar$2d$days$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__CalendarDays$3e$__["CalendarDays"], {
                        size: 28,
                        className: "text-gray-400 dark:text-gray-500"
                    }, void 0, false, {
                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                        lineNumber: 118,
                        columnNumber: 11
                    }, this)
                }, void 0, false, {
                    fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                    lineNumber: 117,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                            className: "text-lg font-semibold text-gray-700 dark:text-gray-300",
                            children: "Aucun emploi du temps généré"
                        }, void 0, false, {
                            fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                            lineNumber: 121,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            className: "text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-xs mx-auto",
                            children: "Configurez vos données et lancez la génération depuis l'espace de travail."
                        }, void 0, false, {
                            fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                            lineNumber: 124,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                    lineNumber: 120,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"], {
                    href: "/workspace",
                    className: "mt-2 px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-700 transition-colors",
                    children: "Aller à l'espace de travail"
                }, void 0, false, {
                    fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                    lineNumber: 128,
                    columnNumber: 9
                }, this)
            ]
        }, void 0, true, {
            fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
            lineNumber: 116,
            columnNumber: 7
        }, this);
    }
    // ── Main ───────────────────────────────────────────────────────────────────
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "animate-fade-in",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "flex flex-wrap items-start justify-between gap-4 mb-6",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h1", {
                                className: "text-2xl font-bold text-gray-900 dark:text-white",
                                children: "Résultats"
                            }, void 0, false, {
                                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                lineNumber: 144,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                className: "text-sm text-gray-500 dark:text-gray-400 mt-0.5",
                                children: isLoading ? 'Chargement…' : `${assignments.length} session(s) · ${classes.length} classe(s) · ${teachers.length} enseignant(s)`
                            }, void 0, false, {
                                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                lineNumber: 145,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                        lineNumber: 143,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "flex flex-wrap gap-2",
                        children: EXPORT_FORMATS.map((fmt)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                onClick: ()=>handleExport(fmt.id),
                                disabled: !!downloading || isLoading,
                                className: "flex items-center gap-1.5 px-3 py-2 border border-gray-200 dark:border-gray-700 text-sm rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors disabled:opacity-50 text-gray-700 dark:text-gray-300",
                                children: [
                                    downloading === fmt.id ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$loader$2d$circle$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Loader2$3e$__["Loader2"], {
                                        size: 14,
                                        className: "animate-spin"
                                    }, void 0, false, {
                                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                        lineNumber: 163,
                                        columnNumber: 19
                                    }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$file$2d$down$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__FileDown$3e$__["FileDown"], {
                                        size: 14
                                    }, void 0, false, {
                                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                        lineNumber: 164,
                                        columnNumber: 19
                                    }, this),
                                    fmt.label
                                ]
                            }, fmt.id, true, {
                                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                lineNumber: 156,
                                columnNumber: 13
                            }, this))
                    }, void 0, false, {
                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                        lineNumber: 154,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                lineNumber: 142,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "flex gap-1 mb-5 bg-gray-100 dark:bg-gray-800 p-1 rounded-xl w-fit overflow-x-auto",
                children: TABS.map((tab)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                        onClick: ()=>{
                            setActiveTab(tab.id);
                            setSelected('');
                        },
                        className: [
                            'px-3 sm:px-4 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap',
                            activeTab === tab.id ? 'bg-white dark:bg-gray-900 text-teal-700 dark:text-teal-400 shadow-sm' : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                        ].join(' '),
                        children: tab.label
                    }, tab.id, false, {
                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                        lineNumber: 175,
                        columnNumber: 11
                    }, this))
            }, void 0, false, {
                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                lineNumber: 173,
                columnNumber: 7
            }, this),
            activeTab === 'subject' ? isLoading ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(GridSkeleton, {}, void 0, false, {
                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                lineNumber: 192,
                columnNumber: 21
            }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm overflow-hidden overflow-x-auto",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("table", {
                    className: "w-full text-sm min-w-[480px]",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("thead", {
                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("tr", {
                                className: "border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("th", {
                                        className: "px-5 py-3 text-left font-semibold text-gray-700 dark:text-gray-300",
                                        children: "Matière"
                                    }, void 0, false, {
                                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                        lineNumber: 197,
                                        columnNumber: 19
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("th", {
                                        className: "px-5 py-3 text-center font-semibold text-gray-700 dark:text-gray-300",
                                        children: "Sessions"
                                    }, void 0, false, {
                                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                        lineNumber: 198,
                                        columnNumber: 19
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("th", {
                                        className: "px-5 py-3 text-left font-semibold text-gray-700 dark:text-gray-300",
                                        children: "Enseignants"
                                    }, void 0, false, {
                                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                        lineNumber: 199,
                                        columnNumber: 19
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("th", {
                                        className: "px-5 py-3 text-left font-semibold text-gray-700 dark:text-gray-300",
                                        children: "Classes"
                                    }, void 0, false, {
                                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                        lineNumber: 200,
                                        columnNumber: 19
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                lineNumber: 196,
                                columnNumber: 17
                            }, this)
                        }, void 0, false, {
                            fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                            lineNumber: 195,
                            columnNumber: 15
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("tbody", {
                            children: subjectSummary.map((row, i)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("tr", {
                                    className: `border-b border-gray-100 dark:border-gray-800 last:border-0 ${i % 2 !== 0 ? 'bg-gray-50/50 dark:bg-gray-800/20' : ''}`,
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("td", {
                                            className: "px-5 py-3 font-medium text-gray-900 dark:text-gray-100",
                                            children: row.subject
                                        }, void 0, false, {
                                            fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                            lineNumber: 211,
                                            columnNumber: 21
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("td", {
                                            className: "px-5 py-3 text-center",
                                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                className: "bg-teal-100 dark:bg-teal-900/40 text-teal-700 dark:text-teal-300 text-xs px-2.5 py-0.5 rounded-full font-medium",
                                                children: row.sessions
                                            }, void 0, false, {
                                                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                                lineNumber: 213,
                                                columnNumber: 23
                                            }, this)
                                        }, void 0, false, {
                                            fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                            lineNumber: 212,
                                            columnNumber: 21
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("td", {
                                            className: "px-5 py-3 text-gray-600 dark:text-gray-400",
                                            children: row.teachers.join(', ')
                                        }, void 0, false, {
                                            fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                            lineNumber: 217,
                                            columnNumber: 21
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("td", {
                                            className: "px-5 py-3 text-gray-600 dark:text-gray-400",
                                            children: row.classes.join(', ')
                                        }, void 0, false, {
                                            fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                            lineNumber: 218,
                                            columnNumber: 21
                                        }, this)
                                    ]
                                }, row.subject, true, {
                                    fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                    lineNumber: 205,
                                    columnNumber: 19
                                }, this))
                        }, void 0, false, {
                            fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                            lineNumber: 203,
                            columnNumber: 15
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                    lineNumber: 194,
                    columnNumber: 13
                }, this)
            }, void 0, false, {
                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                lineNumber: 193,
                columnNumber: 11
            }, this) : /* ── Grid views ── */ /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Fragment"], {
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "flex flex-wrap items-center gap-3 mb-4",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("label", {
                                className: "text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap",
                                children: [
                                    activeTab === 'class' && 'Classe :',
                                    activeTab === 'teacher' && 'Enseignant :',
                                    activeTab === 'room' && 'Salle :'
                                ]
                            }, void 0, true, {
                                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                lineNumber: 229,
                                columnNumber: 13
                            }, this),
                            isLoading ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "h-9 w-40 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse"
                            }, void 0, false, {
                                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                lineNumber: 235,
                                columnNumber: 15
                            }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("select", {
                                value: resolvedSelected,
                                onChange: (e)=>setSelected(e.target.value),
                                className: "px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500",
                                children: options.map((o)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("option", {
                                        value: o,
                                        children: o
                                    }, o, false, {
                                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                        lineNumber: 242,
                                        columnNumber: 35
                                    }, this))
                            }, void 0, false, {
                                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                lineNumber: 237,
                                columnNumber: 15
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                        lineNumber: 228,
                        columnNumber: 11
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm overflow-x-auto",
                        children: isLoading ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(GridSkeleton, {}, void 0, false, {
                            fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                            lineNumber: 249,
                            columnNumber: 15
                        }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "p-4 min-w-[560px]",
                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$components$2f$TimetableGrid$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"], {
                                assignments: filtered,
                                days: days,
                                view: activeTab
                            }, void 0, false, {
                                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                lineNumber: 252,
                                columnNumber: 17
                            }, this)
                        }, void 0, false, {
                            fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                            lineNumber: 251,
                            columnNumber: 15
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                        lineNumber: 247,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true),
            softResults.length > 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "mt-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm p-5",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                        className: "text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4",
                        children: "Contraintes souples"
                    }, void 0, false, {
                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                        lineNumber: 262,
                        columnNumber: 11
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "space-y-3",
                        children: softResults.map((s, i)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "flex items-center gap-3",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: `w-2 h-2 rounded-full flex-shrink-0 ${s.satisfied ? 'bg-teal-500' : 'bg-amber-400'}`
                                    }, void 0, false, {
                                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                        lineNumber: 268,
                                        columnNumber: 17
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "flex-1 text-sm text-gray-700 dark:text-gray-300 leading-snug",
                                        children: s.description
                                    }, void 0, false, {
                                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                        lineNumber: 273,
                                        columnNumber: 17
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "flex items-center gap-2 flex-shrink-0",
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                className: "w-20 h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden",
                                                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                    className: `h-full rounded-full transition-all duration-700 ${s.satisfied ? 'bg-teal-500' : 'bg-amber-400'}`,
                                                    style: {
                                                        width: `${s.score}%`
                                                    }
                                                }, void 0, false, {
                                                    fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                                    lineNumber: 278,
                                                    columnNumber: 21
                                                }, this)
                                            }, void 0, false, {
                                                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                                lineNumber: 277,
                                                columnNumber: 19
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                className: `text-xs font-semibold w-8 text-right tabular-nums ${s.satisfied ? 'text-teal-600 dark:text-teal-400' : 'text-amber-600 dark:text-amber-400'}`,
                                                children: [
                                                    s.score,
                                                    "%"
                                                ]
                                            }, void 0, true, {
                                                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                                lineNumber: 285,
                                                columnNumber: 19
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                        lineNumber: 276,
                                        columnNumber: 17
                                    }, this)
                                ]
                            }, i, true, {
                                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                                lineNumber: 267,
                                columnNumber: 15
                            }, this))
                    }, void 0, false, {
                        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                        lineNumber: 265,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
                lineNumber: 261,
                columnNumber: 9
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/Desktop/TIMEASE/frontend/app/results/page.tsx",
        lineNumber: 140,
        columnNumber: 5
    }, this);
}
_s(ResultsPage, "noju/+ALiZ61JVIrg/zFoZKSua0=", false, function() {
    return [
        __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$hooks$2f$useSession$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useSession"],
        __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$components$2f$Toast$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useToast"]
    ];
});
_c1 = ResultsPage;
var _c, _c1;
__turbopack_context__.k.register(_c, "GridSkeleton");
__turbopack_context__.k.register(_c1, "ResultsPage");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/Desktop/TIMEASE/frontend/node_modules/lucide-react/dist/esm/icons/file-down.js [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "__iconNode",
    ()=>__iconNode,
    "default",
    ()=>FileDown
]);
/**
 * @license lucide-react v1.7.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$createLucideIcon$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/node_modules/lucide-react/dist/esm/createLucideIcon.js [app-client] (ecmascript)");
;
const __iconNode = [
    [
        "path",
        {
            d: "M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z",
            key: "1oefj6"
        }
    ],
    [
        "path",
        {
            d: "M14 2v5a1 1 0 0 0 1 1h5",
            key: "wfsgrz"
        }
    ],
    [
        "path",
        {
            d: "M12 18v-6",
            key: "17g6i2"
        }
    ],
    [
        "path",
        {
            d: "m9 15 3 3 3-3",
            key: "1npd3o"
        }
    ]
];
const FileDown = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$createLucideIcon$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"])("file-down", __iconNode);
;
}),
"[project]/Desktop/TIMEASE/frontend/node_modules/lucide-react/dist/esm/icons/file-down.js [app-client] (ecmascript) <export default as FileDown>", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "FileDown",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$file$2d$down$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"]
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$file$2d$down$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/node_modules/lucide-react/dist/esm/icons/file-down.js [app-client] (ecmascript)");
}),
"[project]/Desktop/TIMEASE/frontend/node_modules/lucide-react/dist/esm/icons/calendar-days.js [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "__iconNode",
    ()=>__iconNode,
    "default",
    ()=>CalendarDays
]);
/**
 * @license lucide-react v1.7.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$createLucideIcon$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/node_modules/lucide-react/dist/esm/createLucideIcon.js [app-client] (ecmascript)");
;
const __iconNode = [
    [
        "path",
        {
            d: "M8 2v4",
            key: "1cmpym"
        }
    ],
    [
        "path",
        {
            d: "M16 2v4",
            key: "4m81vk"
        }
    ],
    [
        "rect",
        {
            width: "18",
            height: "18",
            x: "3",
            y: "4",
            rx: "2",
            key: "1hopcy"
        }
    ],
    [
        "path",
        {
            d: "M3 10h18",
            key: "8toen8"
        }
    ],
    [
        "path",
        {
            d: "M8 14h.01",
            key: "6423bh"
        }
    ],
    [
        "path",
        {
            d: "M12 14h.01",
            key: "1etili"
        }
    ],
    [
        "path",
        {
            d: "M16 14h.01",
            key: "1gbofw"
        }
    ],
    [
        "path",
        {
            d: "M8 18h.01",
            key: "lrp35t"
        }
    ],
    [
        "path",
        {
            d: "M12 18h.01",
            key: "mhygvu"
        }
    ],
    [
        "path",
        {
            d: "M16 18h.01",
            key: "kzsmim"
        }
    ]
];
const CalendarDays = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$createLucideIcon$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"])("calendar-days", __iconNode);
;
}),
"[project]/Desktop/TIMEASE/frontend/node_modules/lucide-react/dist/esm/icons/calendar-days.js [app-client] (ecmascript) <export default as CalendarDays>", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "CalendarDays",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$calendar$2d$days$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"]
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$calendar$2d$days$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/node_modules/lucide-react/dist/esm/icons/calendar-days.js [app-client] (ecmascript)");
}),
"[project]/Desktop/TIMEASE/frontend/node_modules/lucide-react/dist/esm/icons/loader-circle.js [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "__iconNode",
    ()=>__iconNode,
    "default",
    ()=>LoaderCircle
]);
/**
 * @license lucide-react v1.7.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$createLucideIcon$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/node_modules/lucide-react/dist/esm/createLucideIcon.js [app-client] (ecmascript)");
;
const __iconNode = [
    [
        "path",
        {
            d: "M21 12a9 9 0 1 1-6.219-8.56",
            key: "13zald"
        }
    ]
];
const LoaderCircle = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$createLucideIcon$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"])("loader-circle", __iconNode);
;
}),
"[project]/Desktop/TIMEASE/frontend/node_modules/lucide-react/dist/esm/icons/loader-circle.js [app-client] (ecmascript) <export default as Loader2>", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "Loader2",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$loader$2d$circle$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"]
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$Desktop$2f$TIMEASE$2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$loader$2d$circle$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Desktop/TIMEASE/frontend/node_modules/lucide-react/dist/esm/icons/loader-circle.js [app-client] (ecmascript)");
}),
]);

//# sourceMappingURL=Desktop_TIMEASE_frontend_09yicz-._.js.map