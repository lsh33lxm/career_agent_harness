/** 公司头像：无 logoUrl 时使用稳定暖色 + 公司首字；不为不存在的职位伪造商标。 */
const AVATAR_PALETTE: Array<[string, string]> = [
  ["#0a514d", "#e3ece6"],
  ["#77571c", "#f5e7c4"],
  ["#316074", "#e3edf2"],
  ["#6b4a3a", "#f3e6df"],
  ["#4a5d3a", "#e8ecdd"],
  ["#5d4a6b", "#ece5f0"],
];

function hashName(name: string): number {
  let hash = 0;
  for (let index = 0; index < name.length; index += 1) {
    hash = (hash * 31 + name.charCodeAt(index)) | 0;
  }
  return Math.abs(hash);
}

interface CompanyAvatarProps {
  name: string;
  logoUrl?: string | null;
  size?: number;
}

export function CompanyAvatar({ name, logoUrl, size = 34 }: CompanyAvatarProps) {
  const [fg, bg] = AVATAR_PALETTE[hashName(name || "未知") % AVATAR_PALETTE.length];
  const initial = (name.trim()[0] ?? "·").toUpperCase();
  const style = { width: size, height: size, fontSize: Math.round(size * 0.42) };
  if (logoUrl) {
    return (
      <img className="company-avatar" style={style} src={logoUrl} alt="" loading="lazy" />
    );
  }
  return (
    <span className="company-avatar" style={{ ...style, color: fg, background: bg }} aria-hidden="true">
      {initial}
    </span>
  );
}
