export default function Footer() {
  return (
    <footer className="w-full py-8 px-8 flex flex-col md:flex-row justify-between items-center gap-4 border-t border-surface-elevated mt-auto bg-transparent z-10 relative backdrop-blur-sm">
      <div className="flex flex-col items-center md:items-start">
        <div className="text-text-primary font-bold text-lg">TruthMates</div>
        <div className="text-on-surface-variant text-sm mt-1">for the people of India</div>
      </div>
      
      <div className="flex gap-6 text-sm text-on-surface-variant">
        <a href="mailto:contact@truthmates.in" className="hover:text-text-primary transition-colors">Contact Us</a>
        <a href="#" className="hover:text-text-primary transition-colors">Privacy Policy</a>
        <a href="#" className="hover:text-text-primary transition-colors">Terms of Service</a>
      </div>
    </footer>
  )
}
