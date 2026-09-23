import React from "react";
import Icon from "./Icon.jsx";

export const pages = [
  { id: "dashboard", label: "今日／本週", icon: "home" },
  { id: "study", label: "智慧學習", icon: "book" },
  { id: "courses", label: "修課規劃", icon: "list" },
  { id: "graduation", label: "畢業進度", icon: "graduation" },
];

export function Sidebar({ activePage, onNavigate }) {
  return (
    <aside className="sidebar">
      <button
        className="brand"
        type="button"
        onClick={() => onNavigate("dashboard")}
        aria-label="回到今日／本週"
      >
        <span className="brand-icon">
          <Icon name="calendar" size={25} />
        </span>
        <span>
          <strong>校園日程</strong>
          <small>規劃今日，成就未來</small>
        </span>
      </button>
      <nav aria-label="主要功能" className="side-nav">
        {pages.map((page) => (
          <button
            key={page.id}
            className={`nav-item ${activePage === page.id ? "active" : ""}`}
            type="button"
            onClick={() => onNavigate(page.id)}
            aria-current={activePage === page.id ? "page" : undefined}
          >
            <Icon name={page.icon} size={21} />
            <span>{page.label}</span>
          </button>
        ))}
      </nav>
      <p className="sidebar-note">
        學生個人安排系統
        <br />
        本機示範版
      </p>
    </aside>
  );
}

export function MobileNav({ activePage, onNavigate }) {
  return (
    <nav className="mobile-nav" aria-label="主要功能">
      {pages.map((page) => (
        <button
          key={page.id}
          type="button"
          className={activePage === page.id ? "active" : ""}
          onClick={() => onNavigate(page.id)}
          aria-current={activePage === page.id ? "page" : undefined}
        >
          <Icon name={page.icon} size={23} />
          <span>{page.label}</span>
        </button>
      ))}
    </nav>
  );
}
