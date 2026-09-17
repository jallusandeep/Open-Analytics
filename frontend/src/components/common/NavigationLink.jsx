import { Link } from "react-router-dom";

// A real link supplies the browser's Open in new tab menu and Ctrl/Cmd-click.
export default function NavigationLink({ to, onClick, children, ...props }) {
  return <Link to={to} {...props} onClick={(event) => {
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    if (onClick) {
      event.preventDefault();
      onClick(event);
    }
  }}>{children}</Link>;
}
