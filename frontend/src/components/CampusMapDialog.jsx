import React, { useEffect, useState } from "react";
import Icon from "./Icon.jsx";

const maps = {
  fucheng: {
    label: "府城校區",
    views: [
      {
        id: "campus",
        label: "校區總覽",
        src: "/maps/fucheng-campus.png",
        alt: "臺南大學府城校區平面圖，顯示建築、出入口與設施",
      },
      {
        id: "rooms",
        label: "教室配置",
        src: "/maps/fucheng-rooms.png",
        alt: "臺南大學府城校區各棟建築的教室與處室配置圖",
      },
    ],
  },
  rongyu: {
    label: "榮譽校區",
    views: [
      {
        id: "rooms",
        label: "教學中心配置",
        src: "/maps/rongyu-rooms.png",
        alt: "臺南大學榮譽校區教學中心各棟建築與教室配置圖",
      },
    ],
  },
};

export default function CampusMapDialog({
  initialCampus = "fucheng",
  location,
  onClose,
}) {
  const [campus, setCampus] = useState(initialCampus);
  const [viewId, setViewId] = useState(
    initialCampus === "rongyu" ? "rooms" : location ? "rooms" : "campus",
  );
  const [zoom, setZoom] = useState(1);
  const campusInfo = maps[campus];
  const selectedView =
    campusInfo.views.find((view) => view.id === viewId) || campusInfo.views[0];

  useEffect(() => {
    function handleKey(event) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  function chooseCampus(nextCampus) {
    setCampus(nextCampus);
    setViewId(nextCampus === "fucheng" ? "campus" : "rooms");
    setZoom(1);
  }

  return (
    <div
      className="modal-backdrop map-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="map-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="map-title"
      >
        <div className="map-heading">
          <div>
            <h2 id="map-title">校區地圖</h2>
            <p>
              {location
                ? `課堂地點：${location}`
                : "查看兩個校區的建物與教室配置。"}
            </p>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="關閉校區地圖"
          >
            <Icon name="close" />
          </button>
        </div>
        <div className="map-toolbar">
          <div className="segment" role="group" aria-label="選擇校區">
            {Object.entries(maps).map(([id, info]) => (
              <button
                key={id}
                type="button"
                className={campus === id ? "selected" : ""}
                onClick={() => chooseCampus(id)}
              >
                {info.label}
              </button>
            ))}
          </div>
          <div className="map-zoom">
            <button
              type="button"
              className="icon-button"
              onClick={() => setZoom((value) => Math.max(1, value - 0.25))}
              disabled={zoom <= 1}
              aria-label="縮小地圖"
            >
              <Icon name="zoomOut" size={18} />
            </button>
            <span>{Math.round(zoom * 100)}%</span>
            <button
              type="button"
              className="icon-button"
              onClick={() => setZoom((value) => Math.min(2.5, value + 0.25))}
              disabled={zoom >= 2.5}
              aria-label="放大地圖"
            >
              <Icon name="zoomIn" size={18} />
            </button>
          </div>
        </div>
        {campusInfo.views.length > 1 && (
          <div className="map-view-tabs" role="group" aria-label="選擇地圖類型">
            {campusInfo.views.map((view) => (
              <button
                type="button"
                key={view.id}
                className={selectedView.id === view.id ? "active" : ""}
                onClick={() => {
                  setViewId(view.id);
                  setZoom(1);
                }}
              >
                {view.label}
              </button>
            ))}
          </div>
        )}
        <div className="map-image-viewport">
          <img
            key={selectedView.src}
            src={selectedView.src}
            alt={selectedView.alt}
            style={{ width: `${zoom * 100}%` }}
          />
        </div>
        <div className="map-footer">
          <span>圖片由使用者提供。教室安排請以實際課表與校方公告為準。</span>
          <a href={selectedView.src} target="_blank" rel="noopener noreferrer">
            開啟原圖 <Icon name="right" size={15} />
          </a>
        </div>
      </section>
    </div>
  );
}
