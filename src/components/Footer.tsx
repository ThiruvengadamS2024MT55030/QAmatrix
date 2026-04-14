import { Link } from "react-router-dom";
import { Shield } from "lucide-react";

const Footer = () => {
  return (
    <footer className="border-t border-border bg-card/60 mt-auto">
      <div className="max-w-[1800px] mx-auto px-4 py-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-primary/10">
              <Shield className="w-4 h-4 text-primary" />
            </div>
            <span className="text-sm font-bold">QA Matrix</span>
            <span className="text-xs text-muted-foreground">— Quality Assurance System</span>
          </div>
          <nav className="flex items-center gap-6 text-xs">
            <Link to="/" className="text-muted-foreground hover:text-primary transition-colors font-medium">
              Matrix
            </Link>
            <Link to="/defect-upload" className="text-muted-foreground hover:text-primary transition-colors font-medium">
              Defect Upload
            </Link>
            <Link to="/how-it-works" className="text-muted-foreground hover:text-primary transition-colors font-medium">
              How It Works
            </Link>
          </nav>
          <p className="text-[10px] text-muted-foreground">
            © {new Date().getFullYear()} QA Matrix System
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
