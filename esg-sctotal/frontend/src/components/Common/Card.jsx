import React from "react";

const Card = ({ className, onClick, children }) => {
  return (
    <div
      className={"bg-white rounded-xl shadow-sm border border-gray-100 " + (className || "")}
      onClick={onClick}
    >
      {children}
    </div>
  );
};

export default Card;
