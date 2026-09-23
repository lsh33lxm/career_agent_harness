/** 页头右侧的轻量日出点缀：融入状态区，不是独立插画。 */
export function SunriseArt() {
  return (
    <svg className="sunrise-art" viewBox="0 0 168 64" aria-hidden="true" focusable="false">
      <circle cx="96" cy="26" r="17" fill="var(--gold)" opacity="0.75" />
      <ellipse cx="56" cy="56" rx="66" ry="22" fill="var(--green)" opacity="0.10" />
      <ellipse cx="128" cy="58" rx="58" ry="18" fill="var(--green)" opacity="0.07" />
    </svg>
  );
}
